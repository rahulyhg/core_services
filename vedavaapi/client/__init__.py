import requests
from sys import argv
import sys, getopt
import os
import json
import sanskrit_data.schema.common as common_data_containers
from sanskrit_data.schema.users import *
from sanskrit_data.schema.ullekhanam import *

class VedavaapiClient():
    def __init__(self, url):
        self.baseurl = url.rstrip('/')
        self.session = requests.Session()
        self.authenticated = False

    def authenticate(self, creds=None):
        if self.authenticated or not creds:
            return True
        print "Authenticating to Vedavaapi Server with username {} and password {}".format(creds.user, creds.passwd)
        r = self.post("users/v1/password_login", {'user_id' : creds['user'], 'user_secret': creds['passwd'] })
        if not r:
            print "Authentication failed."
        self.authenticated = (r is not None)
        return self.authenticated

    def get(self, url, parms = {}):
        url = self.baseurl + "/" + url
        print "{} {}".format("GET", url)
        try:
            r = self.session.get(url, params=parms)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error("GET on {} returned {}".format(url, e))
            return None

    def post(self, url, parms = {}, files=None):
        url = self.baseurl + "/" + url
        print "{} {}".format("POST", url)
        try:
            #print_dict(parms)
            r = self.session.post(url, data=parms, files=files)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error("POST on {} returned {}".format(url, e))
            return None

    def delete(self, url, parms = {}):
        url = self.baseurl + "/" + url
        print "{} {}".format("DELETE", url)
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

Parms = DotDict({
    'reset' : False,
    'dbgFlag' : True,
    'server_baseurl' : '',
    'auth' : DotDict({'user' : 'vedavaapiAdmin', 'passwd' : '@utoDump1'}),
    'dbname' : ''
    })

(cmddir, cmdname) = os.path.split(__file__)

def usage():
    print(cmdname + " [-r] [-u <userid>:<password>] [-d <dbname>] <server_baseurl> ...")
    exit(1)

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "rd:hu:", ["url="])
    except getopt.GetoptError:
        usage()

    global Parms
    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt in ("-r", "--reset"):
            Parms.reset = True
        elif opt in ("-u", "--auth"):
            Parms.auth = DotDict(dict(zip(('user', 'passwd'), arg.split(':'))))
            print Parms.auth
        elif opt in ("-d", "--db"):
            Parms.dbname = arg

    if not args:
        usage()

    Parms.server_baseurl = args[0]
    client = VedavaapiClient(Parms.server_baseurl)

    # First Authenticate with the Vedavaapi Server
    if Parms.auth.user:
        if not client.authenticate(Parms.auth):
            print "Authentication failed; exiting."
            sys.exit(1)
    else:
        print "Proceeding without authentication ..."

    # Issue API calls
    if not Parms.dbname:
        print "Supply database to use via -d option."
        usage()
    r = client.get("ullekhanam/v1/dbs/{}/entities/{}".format(Parms.dbname,
            "59f92073caae641d29ba7f8e"), 
            { 'depth' : 2 })
    if r:
        print_dict(r.json())
        #books = common_data_containers.JsonObject.make_from_dict_list(r.json())
        #print "retrieved {} ".format(len(books))
        #print_dict(user[0].to_json_map())

if __name__ == "__main__":
   main(sys.argv[1:])
