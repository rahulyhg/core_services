import sys

import flask
import flask_restplus
import furl
from authlib.flask.oauth2 import current_token
from authlib.specs.rfc6749 import OAuth2Error
from flask import session, request, Response
from sanskrit_ld.helpers import permissions_helper
from sanskrit_ld.schema.base import ObjectPermissions
from sanskrit_ld.schema import WrapperObject
from vedavaapi.common.api_common import error_response, abort_with_error_response

from . import api
from ... import get_users_colln, get_authlib_authorization_server, get_authorizer_config, require_oauth, \
    get_current_user_id, get_current_org, sign_out_user, myservice, get_initial_agents
from ....agents_helpers.models import User
from ....agents_helpers.oauth_client_helper import OauthClientsRegistry, OAuthClient


authorization_ns = api.namespace('authorization', path='/')


def redirect_js(redirect_url):
    return 'Continue on to <a href="%(url)s">%(url)s</a>. <script>window.location = "%(url)s";</script>' % {
        "url": redirect_url}


def redirect_js_response(redirect_url, message_if_none, message_if_invalid):
    if redirect_url is not None:
        redirect_furl = furl.furl(redirect_url)
        if not redirect_furl.netloc:
            return {'message': message_if_invalid}, 200
        return Response(redirect_js(redirect_furl.url))
    else:
        return {'message': message_if_none}, 200


@authorization_ns.route('/authorize')
class Authorizer(flask_restplus.Resource):

    get_parser = authorization_ns.parser()
    get_parser.add_argument('client_id', type=str, location='args', required=True)
    get_parser.add_argument('response_type', type=str, location='args', required=True)
    get_parser.add_argument('scope', type=str, location='args', required=True)
    get_parser.add_argument('redirect_uri', type=str, location='args', required=True)
    get_parser.add_argument('state', type=str, location='args', required=True)

    post_parser = authorization_ns.parser()
    post_parser.add_argument('client_id', type=str, location='form', required=True)
    post_parser.add_argument('response_type', type=str, location='form', required=True)
    post_parser.add_argument('scope', type=str, location='form', required=True)
    post_parser.add_argument('redirect_uri', type=str, location='form', required=True)
    post_parser.add_argument('state', type=str, location='form', required=True)

    @authorization_ns.expect(get_parser, validate=True)
    def get(self):
        args = self.get_parser.parse_args()
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()
        current_user = User.get_user(users_colln, _id=current_user_id)

        authorization_server = get_authlib_authorization_server()
        try:
            grant = authorization_server.validate_consent_request(request=request, end_user=current_user)
            print(grant, file=sys.stderr)
        except OAuth2Error as e:
            return error_response(message='invalid api client', code=400, error=str(e))

        if not current_user:
            next_page_url = (
                    get_authorizer_config().get('sign_in_page_uri', None)
                    or flask.url_for('oauth_server_v1.static', filename='signin.html', external=True))
        else:
            next_page_url = (
                    get_authorizer_config().get('consent_page_uri', None)
                    or flask.url_for('oauth_server_v1.static', filename='consent.html', external=True))

        next_page_furl = furl.furl(next_page_url)
        next_page_furl.args.update(args)
        return flask.redirect(next_page_furl.url)

    @authorization_ns.expect(post_parser, validate=True)
    def post(self):
        # TODO referer/origin should be checked
        args = self.post_parser.parse_args()
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()
        current_user = User.get_user(users_colln, _id=current_user_id)
        if not current_user:
            return error_response(message='invalid request', code=400)

        authorization_server = get_authlib_authorization_server()
        return redirect_js(authorization_server.create_authorization_response(grant_user=current_user).location)


@authorization_ns.route('/signin')
class SignIn(flask_restplus.Resource):

    post_parser = authorization_ns.parser()
    post_parser.add_argument('email', type=str, location='form', required=True)
    post_parser.add_argument('password', type=str, location='form', required=True)
    post_parser.add_argument('redirect_url', type=str, location='form')

    @authorization_ns.expect(post_parser, validate=True)
    def post(self):
        args = self.post_parser.parse_args()
        users_colln = get_users_colln()

        email = args.get('email')
        password = args.get('password')

        user = User.get_user(users_colln, email=email)
        if user is None:
            return error_response(message='user not found', code=401)

        if not hasattr(user, 'hashedPassword'):
            return error_response(message='user doesn\'t have vedavaapi account', code=403)
        if not user.check_password(password):
            return error_response(message='incorrect password', code=401)

        current_org = get_current_org()
        session['authentications'] = session.get('authentications', {})
        # noinspection PyProtectedMember
        session['authentications'][current_org] = {"user_id": user._id}

        return redirect_js_response(
            args.get('redirect_url', None),
            'sign in successful',
            'sign in successful, but redirect uri is invalid')


def get_oauth_client(provider_name):
    client_config = myservice().get_external_oauth_clients_config(
        get_current_org(),
        provider_name
    )
    client_class = OauthClientsRegistry.get_client_class(provider_name)
    if client_class is None:
        error = error_response(message='provider not supported', code=404)
        abort_with_error_response(error)
    return client_class(client_config)


@authorization_ns.route('/oauth_signin/<provider_name>')
class OAuthSignIn(flask_restplus.Resource):

    get_parser = authorization_ns.parser()
    get_parser.add_argument('redirect_url', type=str, location='args')

    @authorization_ns.expect(get_parser, validate=True)
    def get(self, provider_name):
        args = self.get_parser.parse_args()
        oauth_client = get_oauth_client(provider_name)  # type: OAuthClient

        if not oauth_client:
            return error_response(
                message='currently oauth provider "{}" not supported.'.format(provider_name),
                code=400)

        callback_url = api.url_for(OAuthCallback, provider_name=provider_name, _external=True)
        return oauth_client.redirect_for_authorization(callback_url=callback_url, state=args.get('redirect_url', ''))


@authorization_ns.route('/oauth_callback/<provider_name>')
class OAuthCallback(flask_restplus.Resource):
    get_parser = authorization_ns.parser()
    get_parser.add_argument('state', type=str, location='args')

    @authorization_ns.expect(get_parser, validate=True)
    def get(self, provider_name):
        users_colln = get_users_colln()
        args = self.get_parser.parse_args()
        oauth_client = get_oauth_client(provider_name)  # type: OAuthClient

        if not oauth_client:
            return error_response(
                message='currently oauth provider "{}" not supported.'.format(provider_name),
                code=400)

        auth_code = oauth_client.extract_auth_code()

        callback_url = api.url_for(OAuthCallback, provider_name=provider_name, _external=True)
        access_token_response = oauth_client.exchange_code_for_access_token(
            auth_code, registered_callback_url=callback_url)
        print(access_token_response, file=sys.stderr)

        userinfo, response_code = oauth_client.get_user_info(access_token_response=access_token_response)
        if 'error' in userinfo:
            return error_response(
                message='error in authenticating',
                code=401
            )
        auth_info = oauth_client.normalized_user_info(userinfo)

        user = User.get_user(users_colln, email=auth_info.email, projection={"_id": 1})
        if user is None:
            user = User()
            user.set_from_dict({
                "email": auth_info.email,
                "externalAuthentications": WrapperObject()
            })
            user_id = User.create_new_user(users_colln, doc=user)
            user._id = user_id

            initial_agents = get_initial_agents()
            User.add_group(
                users_colln, User.get_user_selector_doc(_id=user_id), initial_agents.all_users_group_id)
            permissions_helper.add_to_granted_list(
                users_colln, [user_id], ObjectPermissions.ACTIONS, group_pids=[initial_agents.root_admins_group_id])

            permissions_helper.add_to_granted_list(
                users_colln, [user_id],
                [ObjectPermissions.READ, ObjectPermissions.UPDATE_CONTENT, ObjectPermissions.DELETE],
                user_pids=[user_id]
            )

        User.add_external_authentications(users_colln, User.get_user_selector_doc(_id=user._id), auth_info)

        current_org = get_current_org()
        session['authentications'] = session.get('authentications', {})
        # noinspection PyProtectedMember
        session['authentications'][current_org] = {"user_id": user._id}

        return redirect_js_response(
            args.get('redirect_url', None), 'sign in successful', 'sign in successful, but redirect uri is invalid')


# noinspection PyMethodMayBeStatic
@authorization_ns.route('/signout')
class SignOut(flask_restplus.Resource):

    def get(self):
        current_authentication_details = sign_out_user(get_current_org())
        if not current_authentication_details:
            return error_response(message='not signed in', code=200)
        return {"message": "signout successful"}, 200


@authorization_ns.route('/token')
class Token(flask_restplus.Resource):

    post_parser = authorization_ns.parser()
    post_parser.add_argument('client_id', type=str, location='form')
    post_parser.add_argument('client_secret', type=str, location='form')
    post_parser.add_argument('code', type=str, location='form')
    post_parser.add_argument('grant_type', type=str, location='form')
    post_parser.add_argument('redirect_uri', type=str, location='form')

    @authorization_ns.expect(post_parser, validate=True)
    def post(self):
        authorization_server = get_authlib_authorization_server()
        return authorization_server.create_token_response(request=request)


@authorization_ns.route('/resolve_token')
class TokenResolver(flask_restplus.Resource):

    get_parser = authorization_ns.parser()
    get_parser.add_argument('include_user', type=bool, location='args', default=False)

    @require_oauth()
    def get(self):
        token = current_token
        users_colln = get_users_colln()
        args = self.get_parser.parse_args()

        response = {
            "token": token.access_token,
            "scopes": token.scope.split(),
            "user_id": token.user_id
        }
        if args.get('include_user', False):
            user = User.get_user(users_colln, _id=token.user_id, projection={"permissions": 0, "hashedPassword": 0})
            response['user'] = user.to_json_map()

        return response, 200
