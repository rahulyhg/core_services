import sys

import flask_restplus
from flask import session, Response
from furl import furl

from vedavaapi.common.api_common import error_response, get_current_org

from ...helpers.oauth_helper import OauthClientsRegistry, OAuthClient
from .. import myservice
from . import api


auth_ns = api.namespace('authorizer', path='/', description='authentication namespace')


def redirect_js(redirect_url):
    return 'Continue on to <a href="%(url)s">%(url)s</a>. <script>window.location = "%(url)s";</script>' % {
        "url": redirect_url}


def redirect_js_response(redirect_url, message_if_none, message_if_invalid):
    if redirect_url is not None:
        redirect_furl = furl(redirect_url)
        if not redirect_furl.netloc:
            return {'message': message_if_invalid}, 200
        return Response(redirect_js(redirect_furl.url))
    else:
        return {'message': message_if_none}, 200


def get_oauth_client(provider_name):
    oauth_config = myservice().get_oauth_config(
        get_current_org(),
        provider_name
    )
    if not oauth_config:
        return None
    client_class = OauthClientsRegistry.get_client_class(provider_name)
    if not client_class:
        return None
    current_org_name = get_current_org()
    oauth_config['org_name'] = current_org_name

    return client_class(oauth_config)


@auth_ns.route("/logout")
class LogoutAction(flask_restplus.Resource):
    get_parser = auth_ns.parser()
    get_parser.add_argument('redirect_url', type=str, location='args')

    @auth_ns.expect(get_parser, validate=True)
    def get(self):
        args = self.get_parser.parse_args()

        if 'authorizations' in session:
            if get_current_org() in session['authorizations']:
                session['authorizations'].pop(get_current_org())
                return redirect_js_response(
                    args.get('redirect_url', None),
                    message_if_none='logout successful',
                    message_if_invalid='logged out successfully, but redirect_url is invalid'
                )

        return error_response(message='user not logged in.'), 403


@auth_ns.route('/oauth_login/<string:provider_name>')
class OauthLogin(flask_restplus.Resource):

    get_parser = auth_ns.parser()
    get_parser.add_argument('redirect_url', type=str, location='args')

    @auth_ns.expect(get_parser, validate=True)
    def get(self, provider_name):
        args = self.get_parser.parse_args()
        oauth_client = get_oauth_client(provider_name)  # type: OAuthClient

        if not oauth_client:
            return error_response(
                message='currently oauth provider "{}" not supported.'.format(provider_name),
                code=400)

        callback_url = api.url_for(OauthCallback, provider_name=provider_name, _external=True)

        return oauth_client.redirect_for_authorization(callback_url=callback_url, state=args.get('redirect_url', ''))


@auth_ns.route('/oauth_callback/<string:provider_name>')
class OauthCallback(flask_restplus.Resource):

    get_parser = auth_ns.parser()
    get_parser.add_argument('state', type=str, location='args')

    @auth_ns.expect(get_parser, validate=True)
    def get(self, provider_name):
        args = self.get_parser.parse_args()
        oauth_client = get_oauth_client(provider_name)  # type: OAuthClient

        if not oauth_client:
            return error_response(
                message='currently oauth provider "{}" not supported.'.format(provider_name),
                code=400)

        auth_code = oauth_client.extract_auth_code()

        callback_url = api.url_for(OauthCallback, provider_name=provider_name, _external=True)
        access_token_response = oauth_client.exchange_code_for_access_token(
            auth_code, registered_callback_url=callback_url)
        print(access_token_response, file=sys.stderr)

        userinfo, response_code = oauth_client.get_user_info(access_token_response=access_token_response)
        print(userinfo)
        if 'error' in userinfo:
            return error_response(
                message='error in authenticating',
                code=401
            )
        normalized_userinfo = oauth_client.normalized_user_info(userinfo)

        if 'authorizations' not in session:
            session['authorizations'] = {}

        session['authorizations'][get_current_org()] = {
            'access_token': oauth_client.extract_access_token_from_response(access_token_response),
            'refresh_token': oauth_client.extract_refresh_token_from_response(access_token_response),
            'user_id': normalized_userinfo['uid']
        }

        print(session, normalized_userinfo)

        return redirect_js_response(
            args.get('redirect_url', None),
            message_if_none='login successful',
            message_if_invalid='logged in successfully, but redirect_url is invalid'
        )
