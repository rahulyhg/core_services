import logging
import sys
import os

from vedavaapi.common import VedavaapiService

ServiceObj = None


class VedavaapiStore(VedavaapiService):

    def __init__(self, registry, name, conf):
        super(VedavaapiStore, self).__init__(registry, name, conf)
        import_blueprints_after_service_is_ready(self)

        self.clients = {}
        self.default_repo = None
        for repo in self.all_repos():
            repo_conf = self.repo_conf_for(repo)
            if repo_conf["db_type"] == "couchdb":
                from sanskrit_data.db.implementations import couchdb
                self.clients[repo] = couchdb.CloudantApiClient(url=repo_conf["couchdb_host"])
            elif repo_conf["db_type"] == "mongo":
                from sanskrit_data.db.implementations import mongodb
                self.clients[repo] = mongodb.Client(url=repo_conf["mongo_host"])


    def all_repos(self):
        return list(self.config.get('repos', {}).keys())

    def repo_conf_for(self, repo_id):
        return self.config.get('repos').get(repo_id, None)

    def name_of_db(self, repo_id, db_name_end, collection_name=None):
        if not repo_id in self.all_repos():
            return  None
        return '.'.join(['_'.join([self.repo_conf_for(repo_id).get('db_prefix'), db_name_end])] + ([collection_name] if collection_name else []))

    def names_of_db_from_all_repos(self, db_name_end):
        names = {}
        for repo in self.all_repos():
            name = self.name_of_db(repo, db_name_end)
            if name:
                names[repo] = name
        return names

    def path_to_file_store(self, repo_id, file_store_base_path):
        if not repo_id in self.all_repos():
            return  None
        return os.path.join(self.repo_conf_for(repo_id).get('file_store_root_dir'), file_store_base_path)

    def db_interface_for(self, repo_id, db_name_end, collection_name=None, db_name_frontend=None, file_store_base_path=None, db_type=None):
        db_name = self.name_of_db(repo_id, db_name_end)
        print(repo_id, db_name_end, db_name)
        if db_name is None:
            return None
        external_file_store_path = self.path_to_file_store(repo_id, file_store_base_path) if file_store_base_path else None
        return self.clients[repo_id].get_database_interface(
            db_name_backend='.'.join([db_name, collection_name or db_name]),
            db_name_frontend=db_name_frontend or db_name,
            external_file_store=external_file_store_path, db_type=db_type)

    def db_interfaces_from_all_repos(self, db_name_end, collection_name=None, db_name_frontend=None, file_store_base_path=None, db_type=None):
        # may need this at initialization time for all repos
        db_interfaces = {}
        for repo in self.all_repos():
            db_interfaces[repo] = self.db_interface_for(repo, db_name_end, collection_name, db_name_frontend, file_store_base_path, db_type)
        return db_interfaces

    def delete_db(self, repo_id, db_name_end, collection_names=None, delete_external_file_store=False, file_store_base_path=None):
        db_name = self.name_of_db(repo_id, db_name_end)
        collection_names = [db_name] if not collection_names else [collection_names] if not isinstance(collection_names, list) else collection_names
        if not db_name:
            return
        for collection_name in collection_names:
            self.clients[repo_id].delete_database('.'.join([db_name, collection_name or db_name]))
        if delete_external_file_store and file_store_base_path:
            file_store_path = self.path_to_file_store(repo_id=repo_id, file_store_base_path=file_store_base_path) if file_store_base_path else None
            if file_store_path:
                try:
                    os.system("rm -rf {path}".format(path=file_store_path))
                except Exception as e:
                    logging.error('Error removing {path}: {e}'.format(path=file_store_path, e=e))

    def delete_db_in_all_repos(self, db_name_end, collection_names=None, delete_external_file_store=False, file_store_base_path=None):
        for repo in self.all_repos():
            self.delete_db(repo, db_name_end, collection_names, delete_external_file_store=delete_external_file_store, file_store_base_path=file_store_base_path)


def myservice():
    return ServiceObj


api_blueprints = []


def import_blueprints_after_service_is_ready(service_obj):
    global ServiceObj
    ServiceObj = service_obj
    from .api import apiv1_blueprint
    api_blueprints.append(apiv1_blueprint)
