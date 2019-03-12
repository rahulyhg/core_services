import json
import sys

import flask_restplus
from flask import session, Response
from furl import furl

from vedavaapi.common.api_common import error_response, get_current_org, jsonify_argument, check_argument_type
from vedavaapi.common.token_helper import require_oauth, current_token

from ...helpers.oauth_helper import OauthClientsRegistry, OAuthClient
from .. import myservice
from . import api


auth_ns = api.namespace('authorizer', path='/', description='authentication namespace')


"""
Centralized endpoints for implementing OAuth2 explicit flow.
We can register, these callback uris in provider's redirect_uri settings.
And then route, any external auth requests throgh these endpoints.
"""


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


def get_oauth_client(provider_name, client_name=None):
    oauth_config = myservice().get_oauth_client_config(
        get_current_org(),
        provider_name,
        client_name=client_name
    )
    if not oauth_config:
        return None
    client_class = OauthClientsRegistry.get_client_class(provider_name)
    if not client_class:
        return None
    current_org_name = get_current_org()
    oauth_config['org_name'] = current_org_name

    return client_class(oauth_config)


@auth_ns.route('/authorize/<string:provider_name>')
class OAuthAuthorizer(flask_restplus.Resource):

    get_parser = auth_ns.parser()
    get_parser.add_argument('oauth_client_name', type=str, location='args', required=True)
    get_parser.add_argument('callback_url', type=str, location='args', required=True)
    get_parser.add_argument('scope', type=str, location='args', required=True)

    @auth_ns.expect(get_parser, validate=True)
    @require_oauth()
    def get(self, provider_name):

        if not (current_token.client_id and not current_token.user_id):
            return error_response(message='invalid operation. resource is not in scope of users.')

        args = self.get_parser.parse_args()
        oauth_client = get_oauth_client(provider_name, client_name=args.get('oauth_client_name'))  # type: OAuthClient

        if not oauth_client:
            return error_response(
                message='currently oauth provider "{}" not supported.'.format(provider_name),
                code=400)

        oauth_callback_url = api.url_for(OauthCallback, provider_name=provider_name, _external=True)
        state = {
            "vedavaapi_client_id": current_token.client_id,
            "vedavaapi_access_token": current_token.access_token,
            "client_callback_url": args.get('callback_url'),
            "provider_client_name": args.get('oauth_client_name')
        }

        return oauth_client.redirect_for_authorization(
            callback_url=oauth_callback_url, state=json.dumps(state), scope=args.get('scope', None))


@auth_ns.route('/callback/<string:provider_name>')
class OauthCallback(flask_restplus.Resource):

    get_parser = auth_ns.parser()
    get_parser.add_argument('state', type=str, location='args', required=True)
    get_parser.add_argument('code', type=str, location='args', required=True)

    @auth_ns.expect(get_parser, validate=True)
    def get(self, provider_name):
        args = self.get_parser.parse_args()
        state = jsonify_argument(args.get('state', None), key='state')
        check_argument_type(state, (dict,), key='state')

        oauth_client = get_oauth_client(provider_name, client_name=state.get('provider_client_name', None))  # type: OAuthClient

        if not oauth_client:
            return error_response(
                message='currently oauth provider "{}" not supported. or client_name is invalid'.format(provider_name),
                code=400)

        auth_code = oauth_client.extract_auth_code()

        callback_url = api.url_for(OauthCallback, provider_name=provider_name, _external=True)
        access_token_response = oauth_client.exchange_code_for_access_token(
            auth_code, registered_callback_url=callback_url)


        redirect_furl = furl(state.get('client_callback_url', None))
        redirect_furl.args.update(access_token_response)

        return redirect_js_response(
            redirect_furl.url,
            message_if_none='error',
            message_if_invalid='error'
        )
