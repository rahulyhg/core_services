import glob
import logging
import os


class StoreHelper(object):

    allowed_file_store_types = ['data', 'conf', 'creds', 'tmp', 'log', 'cache', 'www']

    def __init__(self, org_name, service_name, registry):
        self.registry = registry
        self.org_name = org_name
        self.org_config = self.registry.orgs_config[self.org_name]
        self.service_name = service_name

        self.mydb_client = self.get_db_client(self.org_config['db_type'], self.org_config['db_host'])

    # methods dealing with filestore
    def _abs_path(self, file_store_type, base_path):
        if file_store_type not in self.allowed_file_store_types:
            return None

        requested_path = os.path.normpath(os.path.join(
            self.registry.install_path,
            'orgs',
            self.org_config.get('file_store_base_path'),
            self.service_name,
            file_store_type,
            base_path.lstrip('/')
        ))
        return requested_path

    def file_store_path(self, file_store_type, base_path, is_dir=False):
        # our conventional way to get file_path. it creates all directories wanted for leaf.
        requested_path = self._abs_path(file_store_type, base_path)
        # print('requested_path', requested_path)
        if not os.path.exists(os.path.dirname(requested_path)):
            os.makedirs(os.path.dirname(requested_path))
        if is_dir and not os.path.exists(requested_path):
            os.makedirs(requested_path)
        return requested_path

    @staticmethod
    def delete_path(file_path):
        try:
            os.system("rm -rf {path}".format(path=file_path))
        except Exception as e:
            logging.error('Error removing {path}: {e}'.format(path=file_path, e=e))

    @staticmethod
    def list_files(dir_path, suffix_pattern='*'):
        file_list = glob.glob(pathname=os.path.join(dir_path, suffix_pattern))
        return [os.path.basename(f) for f in file_list]

    def delete_data(self):
        data_path = self.file_store_path('data', '')
        self.delete_path(data_path)

    # methods dealing with dbs
    @classmethod
    def get_db_client(cls, db_type, db_host):
        if db_type == 'mongo':
            from vedavaapi.objectdb import mongo, mydb
            mongo_client = mongo.MongoDbClient(host_uri=db_host)
            my_db_client = mydb.MyDbClient(mongo_client)
            return my_db_client

    def db_name(self, db_name_suffix):
        return '_'.join([self.org_config.get('db_prefix'), db_name_suffix])

    def db(self, db_name_suffix):
        db_name = self.db_name(db_name_suffix)
        if db_name is None:
            return None
        return self.mydb_client.get_database(db_name)

    def drop_db(self, db_name_suffix):
        db_name = self.db_name(db_name_suffix)
        self.mydb_client.drop_database(db_name)
