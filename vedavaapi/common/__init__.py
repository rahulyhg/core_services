# -*-encoding:utf-8-*-
"""
Some common utilities.
"""

import json
import logging
import os
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


def bytes_for(string, encoding='utf-8', ensure=False):
    # whether it is py2.7 or py3, or obj is str or unicode or bytes, this method will return bytes.
    if isinstance(string, bytes):
        if ensure:
            return string.decode(encoding).encode(encoding)
        else:
            return string
    else:
        return string.encode(encoding)


def unicode_for(string, encoding='utf-8', ensure=False):
    # whether it is py2.7 or py3, or obj is str or unicode or bytes, this method will return unicode string.
    if isinstance(string, bytes):
        return string.decode(encoding)
    else:
        if ensure:
            return string.encode(encoding).decode(encoding)
        else:
            return string


class ServiceRepo(object):
    """
    interface to repo(file storage, db, etc.), to be specialized for each service according to it's needs
    """
    def __init__(self, service, repo_name):
        self.service = service
        self.store = service.registry.lookup('store')
        self.repo_name = repo_name
        try:
            self.repo_config = json.loads(open(self.file_store_path('conf', 'config.json'), 'rb').read().decode('utf-8'))
        except FileNotFoundError:
            self.repo_config = {}
        self.dbs_config = self.service.config.get('dbs', {})

    def initialize(self):
        pass

    def reset(self):
        for key, val in self.dbs_config.items():
            db_name = val.get('name', None)
            if db_name is None:
                continue
            self.store.drop_db(self.repo_name, db_name)

        self.store.delete_data(self.repo_name, self.service.name)

    def db(self, db_name_suffix):
        return self.store.db(
            repo_name=self.repo_name,
            db_name_suffix=db_name_suffix
        )

    def file_store_path(self, file_store_type, file_store_base_path):
        return self.store.file_store_path(
            self.repo_name,
            self.service.name,
            file_store_type or 'data',
            file_store_base_path)


# Base class for all Vedavaapi Service Modules exporting a RESTful API
class VedavaapiService(object):

    instance = None  # reference to singleton instance object of this service.

    dependency_services = []
    svc_repo_class = ServiceRepo  # this should be customised by each service to it's specialized repo class

    # title for this service, to be used any where like, api title, etc.
    title = 'Vedavaapi Service'
    # description for this service.
    description = 'A Vedavaapi service'

    def __init__(self, registry, name, conf=None):
        self.registry = registry  # type: VedavaapiServices
        self.name = name
        self.config = conf if conf is not None else {}
        self.repos = {}
        self._update_instance_ref(self)

    # following are methods dealing with repo, like init, get, reset repo for this service
    def init_repo(self, repo_name):
        """
        initializes repo with given repo_name for this service
        :param repo_name:
        :return:
        """
        if repo_name not in self.repos:
            repo = self.svc_repo_class(self, repo_name)
            self.repos[repo_name] = repo
        self.repos[repo_name].initialize()

    def get_repo(self, repo_name):
        """
        our way to get handle over a repo for this service.
        :param repo_name:
        :return: repo object corresponding to repo_name, and service
        """
        if repo_name not in self.repos:
            self.init_repo(repo_name)
        return self.repos[repo_name]

    def reset_repo(self, repo_name):
        """
        resets the repo
        :param repo_name:
        :return:
        """
        if repo_name not in self.repos:
            repo = self.svc_repo_class(self, repo_name)
            self.repos[repo_name] = repo
        self.repos[repo_name].reset()


    # methods dealing with api plugging.
    @classmethod
    def _update_instance_ref(cls, instance):
        cls.instance = instance

    def _host_module(self):
        """
        gets host module, which is hosting this service
        :return: module object
        """
        modname = "vedavaapi.{}".format(self.name)
        mod = __import__(modname, globals(), locals(), ["*"])
        return mod


    def plug_blueprints(self):
        """
        plugs blueprints to be registered, by appending them to api_blueprints array in service instance
        by default, only plugs blueprint attrs starting with string 'api_blueprint' are plugged
        for any custom behaviour, or to plug other blueprints, etc, override this method for that service
        :return: api_blueprints array in the module
        """
        # mod = self._host_module()
        api_blueprints = getattr(self, 'api_blueprints', None)
        if api_blueprints is None:
            api_blueprints = []
            setattr(self, 'api_blueprints', api_blueprints)

        api_modname = 'vedavaapi.{}.api'.format(self.name)
        try:
            api_mod = __import__(api_modname, globals(), locals(), ["*"])
        except Exception as mnfe:
            return None

        import flask  # just to check if an obj is flask.Blueprint obj or not. independent of context
        blueprints = [
            getattr(api_mod, bp_attr) for bp_attr in dir(api_mod)
            if isinstance(getattr(api_mod, bp_attr), flask.Blueprint) and (re.match('api_blueprint', bp_attr))
        ]
        for blueprint in blueprints:
            if blueprint not in api_blueprints:
                api_blueprints.append(blueprint)

        # print('service:{}, blueprints:{}'.format(self.name, api_blueprints))

        return api_blueprints

    def register_api(self, flask_app, url_prefix):
        # host_mod = self._host_module()
        api_blueprints = getattr(self, 'api_blueprints', None)
        if api_blueprints is None or not len(api_blueprints):
            logging.info("No API service for service {}".format(self.name))
        for api_blueprint in api_blueprints:
            flask_app.register_blueprint(api_blueprint, url_prefix=url_prefix)


# Registry for all Vedavaapi API-based Service Modules
class VedavaapiServices:
    all_services = {}
    install_path = None
    server_config = None

    @classmethod
    def set_config(cls, install_path):
        cls.install_path = install_path
        config_root_dir = os.path.join(cls.install_path, 'conf')
        cls.server_config = {}
        services_config_dir = os.path.join(config_root_dir, 'services')
        all_services = [config_file.split('.')[0] for config_file in os.listdir(services_config_dir)]
        for service in all_services:
            service_config_file = os.path.join(config_root_dir, 'services', '{service}.json'.format(service=service))
            with open(service_config_file, 'rb') as fhandle:
                cls.server_config[service] = json.loads(fhandle.read().decode('utf-8'))
        # print(cls.server_config)

    @classmethod
    def register(cls, svcname, service):
        cls.all_services[svcname] = service

    @classmethod
    def lookup(cls, svcname):
        # print("In lookup({}): {}".format(svcname, cls.all_services))
        return cls.all_services[svcname] if svcname in cls.all_services else None  # type: VedavaapiService

    @classmethod
    def service_class_name(cls, service_name):
        return "Vedavaapi" + ''.join(x.capitalize() or '_' for x in service_name.split('_'))

    @classmethod
    def start(cls, app, svcname, reset=False):
        logging.info("Starting vedavaapi.{} service ...".format(svcname))
        svc_cls = cls.service_class_name(svcname)
        _tmp = __import__('vedavaapi.{}'.format(svcname), globals(), locals(), [svc_cls])
        svc_cls = eval('_tmp.' + svc_cls)

        try:
            for dep in svc_cls.dependency_services:
                if dep in cls.all_services.keys():
                    # print(dep+' already inited')
                    continue
                # print(dep+' not yet inited')
                cls.start(app, dep, reset=reset)
        except Exception as e:
            raise e

        svc_conf = cls.server_config[svcname] if svcname in cls.server_config else {}
        svc = svc_cls(cls, svcname, svc_conf)
        cls.register(svcname, svc)

        if reset:
            logging.info("Resetting previous state of {} ...".format(svcname))
            for repo_name in cls.lookup('store').repo_names():
                svc.reset_repo(repo_name)
                svc.init_repo(repo_name)
            # cls.lookup("store")
        # svc_obj.setup()
        svc.plug_blueprints()
        svc.register_api(app, "/{}".format(svcname))


def start_app(app, install_path, services, reset=False):
    if not services:
        return

    VedavaapiServices.set_config(install_path=install_path)

    logging.info("install_path: " + app.root_path)
    for svc in services:
        if svc in VedavaapiServices.all_services:
            continue
        VedavaapiServices.start(app, svc, reset)
