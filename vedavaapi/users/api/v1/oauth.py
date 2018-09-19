import json
import logging, os.path

import flask
from flask import url_for
import requests
from furl import furl

from ... import myservice

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


class OAuthClient(object):
    oauth_client_classes = {}
    oauth_client_objects = {}

    def __init__(self, name):
        self.name = name

    # step1
    def redirect_for_authorization(self, next_url):
        pass

    # step2
    def extract_auth_code(self):
        pass

    # step3
    def exchange_code_for_access_token(self, auth_code):
        pass

    def extract_access_token_from_response(self, atr):
        pass

    # step4
    def get_user_info(self, access_token_response):
        pass

    def user_info_in_standard_format(self, userinfo):
        pass

    @classmethod
    def register_provider_class(cls, provider_name, provider_class):
        cls.oauth_client_classes[provider_name] = provider_class

    @classmethod
    def get_client_for_provider(cls, provider_name, refresh=False):
        if provider_name in cls.oauth_client_objects:
            if not refresh:
                return cls.oauth_client_objects[provider_name]

        oauth_config = myservice().config['oauth']
        provider_specific_config = oauth_config.get(provider_name)

        provider_class = cls.oauth_client_classes.get(provider_name)
        if not (provider_class and provider_specific_config):
            return None

        cls.oauth_client_objects[provider_name] = provider_class(config=provider_specific_config)

        return cls.oauth_client_objects[provider_name]


class GoogleClient(OAuthClient):
    userinfo_api_endpoint = 'https://www.googleapis.com/oauth2/v3/userinfo'

    def __init__(self, config):
        super(GoogleClient, self).__init__(name='google')
        client_secret_path = os.path.join(config['base_dir'], config['client_secret_file'])
        client_secret_data = json.load(open(client_secret_path))
        self.me = {}
        for key in client_secret_data:
            self.me.update(client_secret_data[key])
            # should hardcode type of creds instead of this.

    def redirect_for_authorization(self, next_url):
        callback_redirect_uri = url_for('.oauth_authorized', provider_name=self.name, _external=True)

        params = {
            'response_type': 'code',
            'client_id': self.me['client_id'],
            'redirect_uri': callback_redirect_uri,
            # 'scope' : 'openid email',
            'scope': 'email',
            'state': next_url
        }

        google_redirect_furl = furl(self.me['auth_uri'])
        google_redirect_furl.args.update(params)
        return flask.redirect(google_redirect_furl.url)

    def extract_auth_code(self):
        return flask.request.args['code']

    def exchange_code_for_access_token(self, auth_code):

        request_data = {
            'grant_type': 'authorization_code',
            'client_id': self.me['client_id'],
            'client_secret': self.me['client_secret'],
            'redirect_uri': url_for('.oauth_authorized', provider_name=self.name, _external=True),
            'code': auth_code
        }

        atr = requests.post(self.me['token_uri'], data=request_data)

        # access_token = atr.json().get('access_token')

        return atr.json()

    def extract_access_token_from_response(self, atr):
        if not atr:
            return None
        return atr['access_token'] if 'access_token' in atr else None

    def get_user_info(self, access_token_response):
        auth_headers = {
            'Authorization': access_token_response.get('token_type', 'Bearer') + ' ' + access_token_response[
                'access_token']}

        response = requests.get(self.userinfo_api_endpoint, headers=auth_headers)

        return response.json(), response.status_code

    def user_info_in_standard_format(self, userinfo):
        info = {
            'email': userinfo['email'],
            'name': userinfo['name'],
            'profile': userinfo['profile'],
            'picture': userinfo['picture'],
            'provider': self.name,
            'raw_provider_response': userinfo
        }

        return info


OAuthClient.register_provider_class('google', GoogleClient)


class FacebookClient(OAuthClient):
    userinfo_api_endpoint = 'https://graph.facebook.com/me'

    def __init__(self, config):
        super(FacebookClient, self).__init__(name='facebook')
        client_secret_path = os.path.join(config['base_dir'], config['client_secret_file'])
        client_secret_data = json.load(open(client_secret_path))
        self.me = {}
        for key in client_secret_data:
            self.me.update(client_secret_data[key])
            # should hardcode type of creds instead of this.

    def redirect_for_authorization(self, next_url):
        callback_redirect_uri = url_for('.oauth_authorized', provider_name=self.name, _external=True)  # only HTTPS

        params = {
            'response_type': 'code granted_scopes',
            'client_id': self.me['client_id'],
            'redirect_uri': callback_redirect_uri,
            'scope': ','.join(['email']),
            'state': next_url
        }

        facebook_redirect_furl = furl(self.me['auth_uri'])
        facebook_redirect_furl.args.update(params)
        return flask.redirect(facebook_redirect_furl.url)

    def extract_auth_code(self):
        return flask.request.args['code']

    def exchange_code_for_access_token(self, auth_code):

        request_params = {
            'client_id': self.me['client_id'],
            'client_secret': self.me['client_secret'],
            'redirect_uri': url_for('.oauth_authorized', provider_name=self.name, _external=True),
            'code': auth_code
        }

        atr = requests.get(self.me['token_uri'], params=request_params)

        return atr.json()

    def extract_access_token_from_response(self, atr):
        if not atr:
            return None
        return atr['access_token'] if 'access_token' in atr else None

    def get_user_info(self, access_token_response):
        import hashlib, hmac, base64
        dig = hmac.new(self.me['client_secret'].encode('utf-8'),
                       msg=access_token_response['access_token'].encode('utf-8'), digestmod=hashlib.sha256)
        appsecret_proof = dig.hexdigest()
        request_params = {
            'access_token': access_token_response['access_token'],
            'appsecret_proof': appsecret_proof,
            'fields': ','.join(['email', 'name', 'id', 'picture'])
        }

        response = requests.get(self.userinfo_api_endpoint, params=request_params)

        return response.json(), response.status_code

    def user_info_in_standard_format(self, userinfo):
        info = {
            'email': userinfo['email'],
            'name': userinfo['name'],
            'profile': userinfo['id'],
            'picture': userinfo['picture'],
            'provider': self.name,
            'raw_provider_response': userinfo
        }

        return info


OAuthClient.register_provider_class('facebook', FacebookClient)

# TODO separate oauth functionality to seperate generic package
