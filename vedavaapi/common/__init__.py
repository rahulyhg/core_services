# -*-encoding:utf-8-*-
"""
Some common utilities.
"""

import json
import logging
import os

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


def bytes_for(astring, encoding='utf-8', ensure=False):
    # whether it is py2.7 or py3, or obj is str or unicode or bytes, this method will return bytes.
    if isinstance(astring, bytes):
        if ensure:
            return astring.decode(encoding).encode(encoding)
        else:
            return astring
    else:
        return astring.encode(encoding)


def unicode_for(astring, encoding='utf-8', ensure=False):
    # whether it is py2.7 or py3, or obj is str or unicode or bytes, this method will return unicode string.
    if isinstance(astring, bytes):
        return astring.decode(encoding)
    else:
        if ensure:
            return astring.encode(encoding).decode(encoding)
        else:
            return astring


# Base class for all Vedavaapi Service Modules exporting a RESTful API
class VedavaapiService(object):
    config_template = {}
    '''
    explicit declaration of services whom this service uses(depends upon).
    when starting this service, we can start it's dependency services first.
    otherwise it will be problem, if services initialized in wrong order, and one service accessed it's dependency in it's initiation
    '''
    dependency_services = []

    def __init__(self, registry, name, conf={}):
        self.registry = registry
        self.name = name
        self.config = conf

    def setup(self, repos=None):
        '''

        :param repos: if we want to setup only perticular repos, then pass array of repo_ids.
                        by default, setups all repos.
        :return:
        '''
        pass

    def reset(self, repos=None):
        '''

        :param repos: if we want to reset only perticular repos, then pass array of repo_ids.
                        by default, resets all repos.
        :return:
        '''
        pass

    def register_api(self, flaskApp, url_prefix):
        modname = "vedavaapi.{}".format(self.name)
        try:
            mod = __import__(modname, globals(), locals(), ["*"])
        except Exception as e:
            logging.info("Cannot load module ", modname)
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
    config_root_dir = None
    server_config = None

    @classmethod
    def set_config(cls, config_root_dir):
        """
        Reads the server configuration from the specified directory for each service, and stores it in the server_config class variable.
        :param config_root_dir:
        :return:
        """
        cls.config_root_dir = config_root_dir
        cls.server_config = {}
        services_config_dir = os.path.join(config_root_dir, 'services')
        all_services = [config_file.split('.')[0] for config_file in os.listdir(services_config_dir)]
        for service in all_services:
            print(service)
            service_config_file = os.path.join(config_root_dir, 'services', '{service}.json'.format(service=service))
            with open(service_config_file, 'rb') as fhandle:
                cls.server_config[service] = json.loads(fhandle.read().decode('utf-8'))
        print(cls.server_config)

    @classmethod
    def register(cls, svcname, service):
        cls.all_services[svcname] = service

    @classmethod
    def lookup(cls, svcname):
        print("In lookup({}): {}".format(svcname, cls.all_services))
        return cls.all_services[svcname] if svcname in cls.all_services else None

    @classmethod
    def start(cls, app, svcname, reset=False):
        logging.info("Starting vedavaapi.{} service ...".format(svcname))
        svc_cls = "Vedavaapi" + str.capitalize(svcname)
        _tmp = __import__('vedavaapi.{}'.format(svcname), globals(), locals(), [svc_cls])
        svc_cls = eval('_tmp.' + svc_cls)

        try:
            for dep in svc_cls.dependency_services:
                if dep in cls.all_services:
                    continue
                cls.start(app, dep, reset=reset)
        except Exception as e:
            pass

        svc_conf = cls.server_config[svcname] if svcname in cls.server_config else {}
        svc_obj = svc_cls(cls, svcname, svc_conf)
        cls.register(svcname, svc_obj)

        if reset:
            logging.info("Resetting previous state of {} ...".format(svcname))
            svc_obj.reset()
            #cls.lookup("store")
        svc_obj.setup()
        svc_obj.register_api(app, "/{}".format(svcname))


def start_app(app, config_root_dir, services, reset=False):
    if not services:
        return

    VedavaapiServices.set_config(config_root_dir=config_root_dir)

    logging.info("Root path: " + app.root_path)
    for svc in services:
        if svc in VedavaapiServices.all_services:
            continue
        VedavaapiServices.start(app, svc, reset)
