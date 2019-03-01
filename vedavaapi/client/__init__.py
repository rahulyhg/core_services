import logging

import requests

try:
    from urllib.parse import unquote, quote_plus, urljoin
except ImportError:  # Python 2
    # noinspection PyUnresolvedReferences
    from urllib import unquote, quote_plus
    # noinspection PyUnresolvedReferences
    from urlparse import urljoin


class VedavaapiClient(object):
    def __init__(self, base_url, org_name='vedavaapi'):
        # we can pass over repo_name in constructor itself, if we want.
        self.base_url = base_url.rstrip('/') + '/'
        self.org_name = org_name
        self.session = requests.Session()
        self.authenticated = False
        self.access_token = None

    def abs_url(self, url_part):
        return urljoin(urljoin(self.base_url, self.org_name + '/'), url_part)

    def authenticate(self, creds=None):
        if self.authenticated or not creds:
            return True
        print(
            "Authenticating to Vedavaapi Server with username {} and password {}".format(
                creds['email'], creds['password']))
        r = self.post("accounts/oauth/v1/signin", {'email': creds['email'], 'password': creds['password']})
        if not r:
            print("Authentication failed.")
        self.authenticated = (r is not None)
        return self.authenticated

    def authorize_client(self, token_uri, client_id, client_secret):
        request_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        atr = requests.post(token_uri.format(org_name=self.org_name), data=request_data)
        atr.raise_for_status()
        self.access_token = atr.json()['access_token']

    def set_access_token(self, access_token):
        self.access_token = access_token

    @classmethod
    def authorization_header(cls, access_token):
        return 'Bearer {}'.format(access_token) if access_token else None

    @classmethod
    def authorized_headers(cls, headers, access_token):
        if not access_token:
            return
        new_headers = headers.copy()
        new_headers['Authorization'] = cls.authorization_header(access_token)
        return new_headers

    def get(self, url, parms=None, authorize_request=True, **kwargs):
        url = self.abs_url(url)
        parms = parms or {}
        headers = kwargs.pop('headers', {})
        if authorize_request:
            headers = self.authorized_headers(headers, self.access_token)

        print("{} {}".format("GET", url))
        r = self.session.get(url, params=parms, headers=headers)
        r.raise_for_status()
        return r

    def post(self, url, data=None, files=None, authorize_request=True, **kwargs):
        url = self.abs_url(url)
        data = data or {}
        headers = kwargs.get('headers', {})
        if authorize_request:
            headers = self.authorized_headers(headers, self.access_token)

        print("{} {}".format("POST", url))
        r = self.session.post(url, data=data, files=files, headers=headers)
        print(r.json())
        r.raise_for_status()
        return r

    def delete(self, url, data=None, authorize_request=True, **kwargs):
        url = self.abs_url(url)
        data = data or {}
        headers = kwargs.get('headers', {})
        if authorize_request:
            headers = self.authorized_headers(headers, self.access_token)

        print("{} {}".format("POST", url))
        r = self.session.delete(url, data=data, headers=headers)
        r.raise_for_status()
        return r


class DotDict(dict):
    def __getattr__(self, name):
        return self[name]
