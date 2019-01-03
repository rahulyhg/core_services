import requests
from sanskrit_data.schema.ullekhanam import *

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
        self.baseurl = base_url.rstrip('/') + '/'
        self.org_name = org_name
        self.session = requests.Session()
        self.authenticated = False

    def abs_url(self, url_part):
        return urljoin(urljoin(self.baseurl, self.org_name + '/'), url_part)

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

    def post(self, url, parms=None, files=None):
        if parms is None:
            parms = {}
        url = self.abs_url(url)
        print("{} {}".format("POST", url))
        try:
            # print_dict(parms)
            r = self.session.post(url, data=parms, files=files)
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
