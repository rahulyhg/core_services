#!/usr/bin/python -u

"""
This is the main entry point. It does the following

-  starts the webservice (either as an independent flask server, or as an apache WSGI module)
-  sets up actions to be taken when various URL-s are accessed.
"""

# This web app may be run in two modes. See bottom of the file.

import getopt
# from flask.ext.cors import CORS
import logging
import os.path
import sys

from sanskrit_data.schema.common import JsonObject

# Add parent directory to PYTHONPATH, so that vedavaapi_py_api module can be found.
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from vedavaapi import common
from sanskrit_data import file_helper
from vedavaapi.common.flask_helper import app

logging.basicConfig(
  level=logging.INFO,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

params = JsonObject()

params.set_from_dict({
  'config_file' : os.path.join(os.path.dirname(__file__), 'conf_local/server_config.json'), 
  'debug': False,
  'port': 9000,
  'reset': False,
  'services' : ['gservices', 'store', 'users']
})

def setup_app():
    common.start_app(params.config_file, params.services, params.reset)

def main(argv):
    def usage():
        logging.info("run.py [-d] [-r] [--port 4444]...")
        logging.info("run.py -h")
        exit(1)

    global params
    try:
        opts, args = getopt.getopt(argv, "drp:h", ["port=", "debug="])
        for opt, arg in opts:
            if opt == '-h':
                usage()
            if opt == '-r':
                params.reset = True
            elif opt in ("-p", "--port"):
                params.port = int(arg)
            elif opt in ("-d", "--debug"):
                params.debug = True
    except getopt.GetoptError:
        usage()
    if args:
        params.services.extend(args)

    setup_app()

    logging.info("Available on the following URLs:")
    for line in file_helper.run_command(["/sbin/ifconfig"]).split("\n"):
        import re
        m = re.match('\s*inet addr:(.*?) .*', line)
        if m:
            logging.info("    http://" + m.group(1) + ":" + str(params.port) + "/")
    app.run(
        host="0.0.0.0",
        port=params.port,
        debug=params.debug,
        use_reloader=False
    )


if __name__ == "__main__":
  logging.info("Running in stand-alone mode.")
  main(sys.argv[1:])
else:
  logging.info("Likely running as a WSGI app.")
  setup_app()
