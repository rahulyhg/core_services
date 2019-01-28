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

    def authorize(self, token_uri, client_id, client_secret):
        """
        presently only client_credentials grant type supported
        :param token_uri:
        :param client_id:
        :param client_secret:
        :return:
        """
        request_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        atr = requests.post(token_uri.format(org_name=self.org_name), data=request_data)
        return atr.json()


    def get(self, url, parms=None):
        if parms is None:
            parms = {}
        url = self.abs_url(url)
        print("{} {}".format("GET", url))
        try:
            r = self.session.get(url, params=parms)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error("GET on {} returned {}".format(url, e))
            return None

    def post(self, url, data=None, files=None):
        if data is None:
            data = {}
        url = self.abs_url(url)
        print("{} {}".format("POST", url))
        try:
            # print_dict(parms)
            r = self.session.post(url, data=data, files=files)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error("POST on {} returned {}".format(url, e))
            try:
                logging.error("error response: {}".format(r.json()))
            except:
                pass
            return None

    def delete(self, url, parms=None):
        if parms is None:
            parms = {}
        url = self.abs_url(url)
        print("{} {}".format("DELETE", url))
        try:
            r = self.session.delete(url, data=parms)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error("DELETE on {} returned {}".format(url, e))
            return None

class DotDict(dict):
    def __getattr__(self, name):
        return self[name]
