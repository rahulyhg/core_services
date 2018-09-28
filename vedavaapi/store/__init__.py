import logging
import os

from vedavaapi.common import VedavaapiService

ServiceObj = None


class VedavaapiStore(VedavaapiService):

    allowed_file_store_types = ['data', 'conf', 'creds']

    def __init__(self, registry, name, conf):
        super(VedavaapiStore, self).__init__(registry, name, conf)
        import_blueprints_after_service_is_ready(self)

        self.clients = {}
        self.default_repo = None
        for repo_name in self.repo_names():
            repo_conf = self._repo_conf(repo_name)
            db_type = repo_conf['db_type']
            # TODO instead should we create client object too for each request?
            # TODO arrange methods in order
            self.clients[repo_name] = self._db_client(
                db_type,
                repo_conf[{'couchdb': 'couchdb_host', 'mongo': 'mongo_host'}[db_type]]
            )

    # methods dealing with repos
    def _repo_conf(self, repo_name):
        return self.config.get('repos').get(repo_name, None)

    def repo_names(self):
        return list(self.config.get('repos', {}).keys())

    def reset_repo(self, repo_name, service_names=None):
        all_services = self.registry.all_services.copy()
        if service_names is None:
            service_names = all_services.keys()
        for service_name in service_names:
            if service_name not in all_services.keys():
                continue
            service_obj = all_services[service_name]
            service_obj.reset(repo_name)
            service_obj.setup(repo_name)
        return True

    # methods dealing with filestore
    def abs_path(self, repo_name, service_name, file_store_type, base_path):
        '''
        convention to get absolute file_store_path from it's components is abstracted in this.
        so that we can change convention if we want at this place
        '''
        if repo_name not in self.repo_names():
            return None
        if file_store_type not in self.allowed_file_store_types:
            return None
        requested_path = os.path.normpath(os.path.join(
            self.registry.mount_path,
            'repos',
            self._repo_conf(repo_name).get('file_store_base_path'),
            service_name,
            file_store_type,
            base_path))
        return requested_path

    def file_store_path(self, repo_name, service_name, file_store_type, base_path):
        # our conventional way to get file_path. it creates all directories wanted for leaf.
        requested_path = self.abs_path(repo_name, service_name, file_store_type, base_path)
        # print('requested_path', requested_path)
        if not os.path.exists(os.path.dirname(requested_path)):
            os.makedirs(os.path.dirname(requested_path))
        return requested_path

    def delete_file(self, file_path):
        try:
            os.system("rm -rf {path}".format(path=file_path))
        except Exception as e:
            logging.error('Error removing {path}: {e}'.format(path=file_path, e=e))

    def list_files(self, dir_path, suffix_pattern='*'):
        import glob, os
        file_list = glob.glob(pathname=os.path.join(dir_path, suffix_pattern))
        return [os.path.basename(f) for f in file_list]

    def delete_data(self, repo_name, service_name):
        data_path = self.file_store_path(repo_name, service_name, 'data', '')
        self.delete_file(data_path)

    # methods dealing with dbs
    @classmethod
    def _db_client(cls, db_type, db_host):
        if db_type == 'couchdb':
            from sanskrit_data.db.implementations import couchdb
            return couchdb.CloudantApiClient(url=db_host)
        elif db_type == 'mongo':
            from sanskrit_data.db.implementations import mongodb
            return mongodb.Client(url=db_host)

    def db_name(self, repo_name, db_name_suffix, collection_name=None):
        # convention to get db_name from it's components is abstracted in this.
        # so that we can change convention if we want at this place
        if repo_name not in self.repo_names():
            return None
        return '.'.join(
            ['_'.join([self._repo_conf(repo_name).get('db_prefix'), db_name_suffix])] +
            ([collection_name] if collection_name else []))

    def db(self, repo_name, db_name_suffix, collection_name=None, db_name_frontend=None, db_type=None):
        db_name = self.db_name(repo_name, db_name_suffix)
        # print(repo_name, db_name_suffix, db_name)
        if db_name is None:
            return None
        return self.clients[repo_name].get_database_interface(
            db_name_backend='.'.join([db_name, collection_name or db_name]),
            db_name_frontend=db_name_frontend or db_name,
            db_type=db_type)

    def delete_db(self, repo_name, db_name_suffix, collection_names=None):
        db_name = self.db_name(repo_name, db_name_suffix)
        collection_names = [db_name] if not collection_names else [collection_names] if not isinstance(collection_names, list) else collection_names
        if not db_name:
            return
        for collection_name in collection_names:
            self.clients[repo_name].delete_database('.'.join([db_name, collection_name or db_name]))


def myservice():
    return ServiceObj


api_blueprints = []


def import_blueprints_after_service_is_ready(service_obj):
    global ServiceObj
    ServiceObj = service_obj
    from .api import apiv1_blueprint
    api_blueprints.append(apiv1_blueprint)
