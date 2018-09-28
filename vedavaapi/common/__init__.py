# -*-encoding:utf-8-*-
"""
Some common utilities.
"""

import json
import logging
import os


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


class ServiceRepoInterface(object):
    '''
    interface to repo(file storage, db, etc.), to be specialized for each service according to it's needs
    '''
    def __init__(self, service, repo_name):
        self.service = service
        self.store = service.registry.lookup('store')
        self.repo_name = repo_name
        try:
            self.repo_config = json.loads(open(self.file_store_path('conf', 'config.json'), 'rb').read().decode('utf-8'))
        except FileNotFoundError:
            self.repo_config = {}

    def initialize(self):
        pass

    def reset(self):
        pass

    def db(self, db_name_suffix, collection_name=None, db_type=None):
        return self.store.db(
            repo_name=self.repo_name,
            db_name_suffix=db_name_suffix,
            collection_name=collection_name,
            db_type=db_type
        )

    def file_store_path(self, file_store_type, file_store_base_path):
        return self.store.file_store_path(
            self.repo_name,
            self.service.name,
            file_store_type or 'data',
            file_store_base_path)


# Base class for all Vedavaapi Service Modules exporting a RESTful API
class VedavaapiService(object):
    config_template = {}
    dependency_services = []
    repo_interface_class = ServiceRepoInterface  # this should be customised by each survice to their specialized interface class

    def __init__(self, registry, name, conf=None):
        self.registry = registry
        self.name = name
        self.config = conf if conf is not None else {}
        self.repos = {}

    def setup(self, repo_name):
        if repo_name not in self.repos:
            repo = self.repo_interface_class(self, repo_name)
            self.repos[repo_name] = repo
        self.repos[repo_name].initialize()

    def get_repo(self, repo_name):
        if repo_name not in self.repos:
            self.setup(repo_name)
        return self.repos[repo_name]

    def reset(self, repo_name):
        if repo_name not in self.repos:
            repo = self.repo_interface_class(self, repo_name)
            self.repos[repo_name] = repo
        self.repos[repo_name].reset()

    def register_api(self, flask_app, url_prefix):
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
                    flask_app.register_blueprint(api_blueprint, url_prefix=url_prefix)
        except Exception as e:
            logging.info("No API service for {}: {}".format(modname, e))
            return
        pass


# Registry for all Vedavaapi API-based Service Modules
class VedavaapiServices:
    all_services = {}
    mount_dir = None
    server_config = None

    @classmethod
    def set_config(cls, mount_path):
        cls.mount_path = mount_path
        config_root_dir = os.path.join(cls.mount_path, 'conf')
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
        # print("In lookup({}): {}".format(svcname, cls.all_services))
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
            for repo_name in cls.lookup('store').repo_names():
                svc_obj.reset(repo_name)
                svc_obj.setup(repo_name)
            # cls.lookup("store")
        # svc_obj.setup()
        svc_obj.register_api(app, "/{}".format(svcname))


def start_app(app, mount_path, services, reset=False):
    if not services:
        return

    VedavaapiServices.set_config(mount_path=mount_path)

    logging.info("Mount directory path: " + app.root_path)
    for svc in services:
        if svc in VedavaapiServices.all_services:
            continue
        VedavaapiServices.start(app, svc, reset)
