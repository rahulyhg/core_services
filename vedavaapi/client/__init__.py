import requests
from sys import argv
import sys, getopt
import os
import json
import sanskrit_data.schema.common as common_data_containers
from sanskrit_data.schema.users import *
from sanskrit_data.schema.ullekhanam import *

class VedavaapiClient():
    def __init__(self, base_url, repo_id=None):
        # we can pass over repo_id in constructor itself, if we want.
        self.baseurl = base_url.rstrip('/')
        self.session = requests.Session()
        self.authenticated = False
        setted_repo = self.set_repo(repo_id)
        if repo_id and not setted_repo:
            raise RuntimeError('setting repo {] failed.'.format(repo_id))

    def authenticate(self, creds=None):
        if self.authenticated or not creds:
            return True
        print("Authenticating to Vedavaapi Server with username {} and password {}".format(creds.user, creds.passwd))
        r = self.post("users/v1/password_login", {'user_id' : creds['user'], 'user_secret': creds['passwd'] })
        if not r:
            print("Authentication failed.")
        self.authenticated = (r is not None)
        return self.authenticated

    def set_repo(self, repo_id):
        if not repo_id:
            return None
        r = self.post('store/v1/repo', parms={'repo_id':repo_id})
        if r is None:
            logging.error('setting repo_id to {} failed.'.format(repo_id))
            return None
        self.repo_id = repo_id
        return repo_id

    def get(self, url, parms=None):
        if parms is None:
            parms = {}
        url = self.baseurl + "/" + url
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
        url = self.baseurl + "/" + url
        print("{} {}".format("POST", url))
        try:
            #print_dict(parms)
            r = self.session.post(url, data=parms, files=files)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error("POST on {} returned {}".format(url, e))
            return None

    def delete(self, url, parms=None):
        if parms is None:
            parms = {}
        url = self.baseurl + "/" + url
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

def print_dict(mydict):
    stext = json.dumps(mydict, indent=2, ensure_ascii=False, separators=(',', ': ')).encode('utf-8')
    print(stext)

default_parms = DotDict({
    'reset' : False,
    'dbgFlag' : True,
    'server_baseurl' : '',
    'auth' : DotDict({'user' : 'vedavaapiAdmin', 'passwd' : '@utoDump1'}),
    'repo_id' : 'vedavaapi_test'
    })

(cmddir, cmdname) = os.path.split(__file__)

def usage():
    print(cmdname + " [-r] [-u <userid>:<password>] [-i <repo_id>] <server_baseurl> ...")
    exit(1)

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "ri:hu:", ["url="])
    except getopt.GetoptError:
        usage()

    parms = default_parms.copy()
    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt in ("-r", "--reset"):
            parms.reset = True
        elif opt in ("-u", "--auth"):
            parms.auth = DotDict(dict(zip(('user', 'passwd'), arg.split(':'))))
            print(parms.auth)
        elif opt in ("-i", "--repo_id"):
            parms.repo_id = arg

    if not args:
        usage()

    parms.server_baseurl = args[0]
    client = VedavaapiClient(parms.server_baseurl, parms.repo_id)

    # First Authenticate with the Vedavaapi Server
    if parms.auth.user:
        if not client.authenticate(parms.auth):
            print("Authentication failed; exiting.")
            sys.exit(1)
    else:
        print("Proceeding without authentication ...")

    # Issue API calls
    r = client.get("ullekhanam/v1/books")
    if r:
        print_dict(r.json())
        #books = common_data_containers.JsonObject.make_from_dict_list(r.json())
        #print "retrieved {} ".format(len(books))
        #print_dict(user[0].to_json_map())

if __name__ == "__main__":
   main(sys.argv[1:])
