"""
Some common utilities.
"""

import json
import logging
from flask import Blueprint, request
from .flask_helper import app

logging.basicConfig(
  level=logging.INFO,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

"""Stores the server configuration."""
server_config = None


def set_configuration(config_file_name):
  """
  Reads the server configuration from the specified file, and stores it in the server_config module variable.
  :param config_file_name:
  :return:
  """
  global server_config
  with open(config_file_name) as fhandle:
    server_config = json.loads(fhandle.read())

def get_user():
  from flask import session
  from sanskrit_data.schema.common import JsonObject
  return JsonObject.make_from_dict(session.get('user', None))

def check_permission(db_name="ullekhanam"):
  from flask import session
  user = get_user()
  logging.debug(request.cookies)
  logging.debug(session)
  logging.debug(session.get('user', None))
  logging.debug(user)
  if user is None or not user.check_permission(service=db_name, action="write"):
    return False
  else:
    return True

# Base class for all Vedavaapi Service Modules exporting a RESTful API
class VedavaapiService(object):
    def __init__(self, name, conf={}):
        self.name = name
        self.config = conf

    def setup(self):
        pass

    def reset(self):
        pass

    def register_api(self, flaskApp, url_prefix):
        modname = "vedavaapi.{}".format(self.name)
        try: 
            mod = __import__(modname, globals(), locals(), ["*"])
        except Exception as e: 
            logging.info("Cannot load module ",modname)
            return

        try:
            api_blueprints = eval('mod.api_blueprints')
            if api_blueprints:
                for api_blueprint in mod.api_blueprints:
                    flaskApp.register_blueprint(api_blueprint, url_prefix=url_prefix)
        except Exception as e:
            logging.info("No API service for {}: {}".format(modname, e))
            return
        pass

# Registry for all Vedavaapi API-based Service Modules
class VedavaapiServices:
    all_services = {}

    @classmethod
    def register(cls, svcname, service):
        cls.all_services[svcname] = service

    @classmethod
    def lookup(cls, svcname):
        return cls.all_services[svcname] if svcname in cls.all_services else None

def start_service(name, reset=False):
    logging.info("Starting vedavaapi.{} service ...".format(name))
    svc_cls = "Vedavaapi" + str.capitalize(name)
    _tmp = __import__('vedavaapi.{}'.format(name), globals(), locals(), [svc_cls])
    svc_cls = eval('_tmp.'+svc_cls)
    svc_conf = server_config[name] if name in server_config else {}
    svc_obj = svc_cls(name, svc_conf)
    VedavaapiServices.register(name, svc_obj)

    if reset:
        logging.info("Resetting previous state of {} ...".format(name))
        svc_obj.reset()
    svc_obj.setup()
    svc_obj.register_api(app, "/{}".format(name))

def start_app(config_file, services, reset=False):
    if not services:
        return

    set_configuration(config_file_name=config_file)

    logging.info("Root path: " + app.root_path)
    for svc in services:
        start_service(svc, reset)
