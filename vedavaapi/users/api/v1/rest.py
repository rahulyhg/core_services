import logging

import flask
import flask_restplus
from flask import session, request, Response
from furl import furl
from jsonschema import ValidationError
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.users import AuthenticationInfo, User

from vedavaapi.common.api_common import error_response, get_repo
from . import api
from .oauth import OAuthClient
from .. import get_colln, myservice
from ...helper import UsersDbHelper


def redirect_js(next_url):
    return 'Continue on to <a href="%(url)s">%(url)s</a>. <script>window.location = "%(url)s";</script>' % {
        "url": next_url}


def oauth_client(provider_name):
    oauth_config = myservice().oauth_config(
        get_repo(),
        provider_name
    )
    return OAuthClient.get_client_for_provider(provider_name, oauth_config)


@api.route('/oauth_login/<string:provider_name>')
class OauthLogin(flask_restplus.Resource):
    get_parser = api.parser()
    get_parser.add_argument('next_url', type=str, location='args')

    @api.expect(get_parser, validate=True)
    def get(self, provider_name):
        client = oauth_client(provider_name)
        if not client:
            return error_response(
                message='currently oauth provider with name "{provider_name}" not supported.'.format(
                    provider_name=provider_name),
                code=400
            )
        return client.redirect_for_authorization(next_url=flask.request.args.get('next_url'))


@api.route('/oauth_authorized/<string:provider_name>')
class OauthAuthorized(flask_restplus.Resource):
    get_parser = api.parser()
    get_parser.add_argument('state', type=str, location='args')

    @api.expect(get_parser, validate=True)
    @api.doc(responses={
        200: 'Login success.',
        401: 'Unauthorized.',
    })
    def get(self, provider_name):
        client = oauth_client(provider_name)
        if not client:
            return error_response(
                message='currently oauth provider with name "{provider_name}" not supported.'.format(
                    provider_name=provider_name),
                code=400
            )
        auth_code = client.extract_auth_code()
        access_token_response = client.exchange_code_for_access_token(auth_code)
        userinfo, response_code = client.get_user_info(access_token_response=access_token_response)
        if 'error' in userinfo:
            # TODO should return/redirect to a custom error page instead.
            return error_response(
                message='error in authenticating',
                code=401
            )

        # provider agnostic key value format with data extracted.
        userinfo_standard = client.user_info_in_standard_format(userinfo)

        session['oauth_token'] = client.extract_access_token_from_response(access_token_response)
        session['user'] = get_user(userinfo_standard, client.name).to_json_map()

        next_url = request.args.get('state')
        if next_url is not None:
            next_url_final = furl(next_url)
            if not next_url_final.netloc:
                return {
                           'message': "logged in successfully, but next_url '{}' is invalid url".format(next_url)
                       }, response_code
            if not next_url_final.scheme:
                next_url_final.scheme = "http"
            next_url_final.args["response_code"] = response_code
            from flask import Response
            return Response(redirect_js(next_url_final))
        else:
            return {'message': 'logged in successfully. but, did not get a next_url, it seems!'}, response_code


def get_user(userinfo, provider_name):
    user = UsersDbHelper.get_user_from_auth_info(get_colln(), AuthenticationInfo.from_details(user_id=userinfo['email'], provider=provider_name))
    print(user)
    if user is None:
        user = User.from_details(
            agentClass='Person',
            auth_infos=[AuthenticationInfo.from_details(user_id=userinfo['email'], provider=provider_name)],
            permissions=myservice().get_default_permissions()
        )
    return user


def is_user_admin():
    user = JsonObject.make_from_dict(session.get('user', None))
    logging.debug(session.get('user', None))
    logging.debug(session)
    logging.debug(user)
    if user is None or not user.check_permission(service="users", action="admin"):
        return False
    else:
        return True


@api.route('/current_user')
class CurrentUserHandler(flask_restplus.Resource):
    # noinspection PyMethodMayBeStatic
    @api.doc(responses={
        200: 'Success.',
        401: 'Unknown - you need to be logged in.',
    })
    def get(self):
        """ Get current user details.

        PS: Login with <a href="v1/oauth_login/google" target="new">google oauth in a new tab</a>.
        """
        session_user = JsonObject.make_from_dict(session.get('user', None))
        if session_user is None:
            return error_response(message="No user found, not authorized!", code=401)
        else:
            return [session_user.to_json_map()], 200


@api.route('/password_login')
class PasswordLogin(flask_restplus.Resource):
    post_parser = api.parser()
    post_parser.add_argument('user_id', type=str, location='form')
    post_parser.add_argument('user_secret', type=str, location='form')
    post_parser.add_argument('next_url', type=str, location='form')

    @api.expect(post_parser, validate=True)
    @api.doc(responses={
        200: 'Login success.',
        401: 'Unauthorized.',
    })
    def post(self):
        """ Log in with a password.

        Passwords are convenient for authenticating bots.
        For human debugging - just use Google oauth login as an admin (but ensure that url is localhost, not a bare ip address).
        """
        user_id = request.form.get('user_id')
        user_secret = request.form.get('user_secret')
        user = UsersDbHelper.get_user_from_auth_info(get_colln(), auth_info=AuthenticationInfo.from_details(
            user_id=user_id,
            provider="vedavaapi"))
        logging.debug(user)
        if user is None:
            return error_response(message="No such user_id", code=401)
        else:
            authentication_matches = list(
                filter(lambda info: info.provider == "vedavaapi" and info.check_password(user_secret),
                       user.authentication_infos))
            if not authentication_matches or len(authentication_matches) == 0:
                return error_response(message="Bad pw", code=401)
            session['user'] = user.to_json_map()
        # logging.debug(request.args)
        # Example request.args: {'code': '4/BukA679ASNPe5xvrbq_2aJXD_OKxjQ5BpCnAsCqX_Io', 'state': 'http://localhost:63342/vedavaapi/ullekhanam-ui/docs/v0/html/viewbook.html?_id=59adf4eed63f84441023762d'}
        next_url = request.form.get('next_url')
        if next_url is not None:
            # Not using redirect(next_url) because:
            #   Attempting to redirect to file:///home/vvasuki/ullekhanam-ui/docs/v0/html/viewbook.html?_id=59adf4eed63f84441023762d failed with "unsafe redirect."
            return Response(redirect_js(next_url))
            # return redirect(next_url)
        else:
            return {'message': 'Did not get a next_url, it seems!'}, 200


@api.route("/logout")
class LogoutHandler(flask_restplus.Resource):
    get_parser = api.parser()
    get_parser.add_argument('next_url', type=str, location='args')

    @api.expect(get_parser, validate=True)
    def get(self):
        session.pop('oauth_token', None)
        session.pop('user', None)
        next_url = request.args.get('next_url')
        if next_url is not None:
            return Response(redirect_js(next_url))
        else:
            return {'message': 'Did not get a next_url, it seems!'}, 200


# noinspection PyMethodMayBeStatic
@api.route('/schemas')
@api.route('/schemas')
class SchemaListHandler(flask_restplus.Resource):
    def get(self):
        """Just list the schemas."""
        from sanskrit_data.schema import common, users
        logging.debug(common.get_schemas(common))
        schemas = common.get_schemas(common)
        schemas.update(common.get_schemas(users))
        return schemas, 200
