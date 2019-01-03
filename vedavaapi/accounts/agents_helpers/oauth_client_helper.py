import json
import logging

import flask
import requests
from furl import furl

from sanskrit_ld.schema.users import AuthenticationInfo

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


class OauthClientsRegistry(object):
    client_classes = {}

    @classmethod
    def register_client_class(cls, client_class):
        cls.client_classes[client_class.provider_name] = client_class

    @classmethod
    def get_client_class(cls, provider_name):
        return cls.client_classes.get(provider_name, None)


class OAuthClient(object):

    provider_name = 'provider'

    # noinspection PyUnusedLocal
    def __init__(self, config):
        pass

    # step1
    def redirect_for_authorization(self, callback_url, state):
        pass

    # step2
    def extract_auth_code(self):
        pass

    # step3
    def exchange_code_for_access_token(self, auth_code, registered_callback_url):
        pass

    def extract_access_token_from_response(self, atr):
        pass

    # step4
    def get_user_info(self, access_token_response):
        pass

    def normalized_user_info(self, userinfo):
        pass


class GoogleClient(OAuthClient):

    provider_name = 'google'

    userinfo_api_endpoint = 'https://www.googleapis.com/oauth2/v3/userinfo'

    def __init__(self, config):
        super(GoogleClient, self).__init__(config)
        client_secret_file_path = config['client_secret_file_path']
        client_secret_json = json.load(open(client_secret_file_path))

        self.client_details = {}
        for key in client_secret_json:
            self.client_details.update(client_secret_json[key])
            # should hard code type of creds instead of this.

    def redirect_for_authorization(self, callback_url, state):
        params = {
            'response_type': 'code',
            'client_id': self.client_details['client_id'],
            'redirect_uri': callback_url,
            # 'scope' : 'openid email',
            'scope': 'email',
            'state': state
        }

        google_auth_url = furl(self.client_details['auth_uri'])
        google_auth_url.args.update(params)
        return flask.redirect(google_auth_url.url)

    def extract_auth_code(self):
        return flask.request.args['code']

    def exchange_code_for_access_token(self, auth_code, registered_callback_url):

        request_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_details['client_id'],
            'client_secret': self.client_details['client_secret'],
            'redirect_uri': registered_callback_url,
            'code': auth_code
        }

        atr = requests.post(self.client_details['token_uri'], data=request_data)
        return atr.json()

    def extract_access_token_from_response(self, atr):
        if not atr:
            return None
        return atr.get('access_token', None)

    def get_user_info(self, access_token_response):
        auth_headers = {
            'Authorization': '{} {}'.format(access_token_response.get('token_type', 'Bearer'), access_token_response[
                'access_token'])
        }

        response = requests.get(self.userinfo_api_endpoint, headers=auth_headers)
        return response.json(), response.status_code

    def normalized_user_info(self, userinfo):
        auth_info = AuthenticationInfo()
        auth_info.set_from_dict({
            'email': userinfo['email'],
            'name': userinfo['name'],
            'uid': userinfo['profile'],
            'picture': userinfo['picture'],
            'provider': self.provider_name,
            #  'raw_provider_response': userinfo
        })

        return auth_info


OauthClientsRegistry.register_client_class(GoogleClient)


class FacebookClient(OAuthClient):
    userinfo_api_endpoint = 'https://graph.facebook.com/me'

    def __init__(self, config):
        super(FacebookClient, self).__init__(config)
        client_secret_file_path = config['client_secret_file_path']
        client_secret_json = json.load(open(client_secret_file_path))

        self.client_details = {}
        for key in client_secret_json:
            self.client_details.update(client_secret_json[key])
            # should hardcode type of creds instead of this.

    def redirect_for_authorization(self, callback_url, state):
        params = {
            'response_type': 'code granted_scopes',
            'client_id': self.client_details['client_id'],
            'redirect_uri': callback_url,
            'scope': ','.join(['email']),
            'state': state
        }

        facebook_auth_url = furl(self.client_details['auth_uri'])
        facebook_auth_url.args.update(params)
        return flask.redirect(facebook_auth_url.url)

    def extract_auth_code(self):
        return flask.request.args['code']

    def exchange_code_for_access_token(self, auth_code, registered_callback_url):

        request_params = {
            'client_id': self.client_details['client_id'],
            'client_secret': self.client_details['client_secret'],
            'redirect_uri': registered_callback_url,
            'code': auth_code
        }

        atr = requests.get(self.client_details['token_uri'], params=request_params)

        return atr.json()

    def extract_access_token_from_response(self, atr):
        if not atr:
            return None
        return atr.get('access_token', None)

    def get_user_info(self, access_token_response):
        import hashlib
        import hmac

        dig = hmac.new(
            self.client_details['client_secret'].encode('utf-8'),
            msg=access_token_response['access_token'].encode('utf-8'), digestmod=hashlib.sha256
        )
        appsecret_proof = dig.hexdigest()

        request_params = {
            'access_token': access_token_response['access_token'],
            'appsecret_proof': appsecret_proof,
            'fields': ','.join(['email', 'name', 'id', 'picture'])
        }

        response = requests.get(self.userinfo_api_endpoint, params=request_params)
        return response.json(), response.status_code

    def normalized_user_info(self, userinfo):
        auth_info = AuthenticationInfo()
        auth_info.set_from_dict({
            'email': userinfo['email'],
            'name': userinfo['name'],
            'uid': userinfo['id'],
            'picture': userinfo['picture'],
            'provider': self.provider_name,
            #  'raw_provider_response': userinfo
        })
        return auth_info


OauthClientsRegistry.register_client_class(FacebookClient)
