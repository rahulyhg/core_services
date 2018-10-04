import logging
import os

from vedavaapi.common import VedavaapiService


class VedavaapiStore(VedavaapiService):

    instance = None

    title = 'Vedavaapi Store'
    description = 'service to interact with repo storage and db'

    allowed_file_store_types = ['data', 'conf', 'creds']

    def __init__(self, registry, name, conf):
        super(VedavaapiStore, self).__init__(registry, name, conf)
        self.mydb_clients = {}
        self.default_repo = None
        for repo_name in self.repo_names():
            repo_conf = self._repo_conf(repo_name)
            db_type = repo_conf['db_type']
            # TODO instead should we create client object too for each request?
            self.mydb_clients[repo_name] = self._db_client(
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
        all_services.pop('store', None)
        if service_names is None:
            service_names = all_services.keys()
        for service_name in service_names:
            if service_name not in all_services.keys():
                continue
            service = all_services[service_name]
            service.reset_repo(repo_name)
            service.init_repo(repo_name)
        return True

    # methods dealing with filestore
    def _abs_path(self, repo_name, service_name, file_store_type, base_path):
        """
        convention to get absolute file_store_path from it's components is abstracted in this.
        so that we can change convention if we want at this place
        """
        if repo_name not in self.repo_names():
            return None
        if file_store_type not in self.allowed_file_store_types:
            return None
        requested_path = os.path.normpath(os.path.join(
            self.registry.install_path,
            'repos',
            self._repo_conf(repo_name).get('file_store_base_path'),
            service_name,
            file_store_type,
            base_path))
        return requested_path

    def file_store_path(self, repo_name, service_name, file_store_type, base_path):
        # our conventional way to get file_path. it creates all directories wanted for leaf.
        requested_path = self._abs_path(repo_name, service_name, file_store_type, base_path)
        # print('requested_path', requested_path)
        if not os.path.exists(os.path.dirname(requested_path)):
            os.makedirs(os.path.dirname(requested_path))
        return requested_path

    def delete_path(self, file_path):
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
        self.delete_path(data_path)

    # methods dealing with dbs
    @classmethod
    def _db_client(cls, db_type, db_host):
        '''
        if db_type == 'couchdb':
            from sanskrit_data.db.implementations import couchdb
            return couchdb.CloudantApiClient(url=db_host)
        '''
        if db_type == 'mongo':
            from vedavaapi.objectdb import mongo, mydb
            mongo_client = mongo.MongoDbClient(host_uri=db_host)
            my_db_client = mydb.MyDbClient(mongo_client)
            return my_db_client

    def db_name(self, repo_name, db_name_suffix):
        """
        convention to get db_name from it's components is abstracted in this.
        so that we can change convention if we want at this place
        """
        if repo_name not in self.repo_names():
            return None
        return '_'.join([self._repo_conf(repo_name).get('db_prefix'), db_name_suffix])

    def db(self, repo_name, db_name_suffix):
        db_name = self.db_name(repo_name, db_name_suffix)
        if db_name is None:
            return None
        return self.mydb_clients[repo_name].get_database(db_name)

    def drop_db(self, repo_name, db_name_suffix):
        db_name = self.db_name(repo_name, db_name_suffix)
        self.mydb_clients[repo_name].drop_database(db_name)

