"""
Some common utilities.
"""

import json
import logging
from flask import request

logging.basicConfig(
  level=logging.INFO,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

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
    config_template = {}
    '''
    explicit declaration of services whom this service uses(depends upon).
    when starting this service, we can start it's dependency services first.
    otherwise it will be problem, if services initialized in wrong order, and one service accessed dependency in it's initiation
    '''
    dependency_services = []

    def __init__(self, registry, name, conf={}):
        self.registry = registry
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
    server_config = None

    @classmethod
    def set_config(cls, config_file_name):
        """
        Reads the server configuration from the specified file, and stores it in the server_config module variable.
        :param config_file_name:
        :return:
        """
        with open(config_file_name) as fhandle:
            cls.server_config = json.loads(fhandle.read())

    @classmethod
    def register(cls, svcname, service):
        cls.all_services[svcname] = service

    @classmethod
    def lookup(cls, svcname):
        print ("In lookup({}): {}".format(svcname, cls.all_services))
        return cls.all_services[svcname] if svcname in cls.all_services else None

