import logging

from sanskrit_data.schema.users import User
from vedavaapi.common import VedavaapiService, ServiceRepo

from .helper import UsersDbHelper

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


class UsersRepo(ServiceRepo):
    def __init__(self, service, repo_name):
        super(UsersRepo, self).__init__(service, repo_name)
        self.users_db_config = self.dbs_config['users_db']
        self.users_db = self.db(db_name_suffix=self.users_db_config['name'])
        self.users_colln = self.users_db.get_collection(self.users_db_config['collections']['users'])

    def initialize(self):
        initial_users = self.service.config["initial_users"]
        self.users_colln.create_index(keys_dict={
            "authentication_infos.auth_user_id": 1
        }, index_name="authentication_infos.auth_user_id")

        # Add initial users to the users db if they don't exist.
        logging.info("Add initial users to the users db if they don't exist.")
        if initial_users is None:
            return
        for initial_user_dict in initial_users:
            initial_user = User.make_from_dict(initial_user_dict)
            matching_users = UsersDbHelper.get_matching_users_by_auth_infos(self.users_colln, user=initial_user)
            if len(matching_users) == 0:
                logging.info("Adding: " + str(initial_user))
                # Use this instead of update_doc to auto-generate auth_secret_bcrypt
                initial_user.update_collection(self.users_colln)
            else:
                logging.info("Not adding: " + str(initial_user))


class VedavaapiUsers(VedavaapiService):
    instance = None
    svc_repo_class = UsersRepo
    dependency_services = ['store', 'credentials']

    title = 'Vedavaapi Users'
    description = 'Service managing users, authentication etc.'

    def __init__(self, registry, name, conf):
        super(VedavaapiUsers, self).__init__(registry, name, conf)
        self.vvstore = registry.lookup("store")
        self.default_permissions = self.config["default_permissions"]

    def colln(self, repo_name):
        return self.get_repo(repo_name).users_colln

    def oauth_config(self, repo_name, provider_name):
        oauth_config = self.config['oauth']
        provider_specific_config = oauth_config.get(provider_name)
        provider_specific_config['client_secret_file_path'] = self.registry.lookup('credentials').creds_path(
            repo_name,
            provider_specific_config['client_secret_file_base_path'])
        return provider_specific_config

    def get_default_permissions(self):
        # return a copy instead of actual array, so that any modifications will not have any impact on original
        return self.default_permissions[:]
