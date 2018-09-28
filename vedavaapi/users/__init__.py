import logging

from sanskrit_data.schema.users import User
from vedavaapi.common import VedavaapiService, ServiceRepoInterface

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


ServiceObj = None


class UsersRepoInterface(ServiceRepoInterface):
    def __init__(self, service, repo_name):
        super(UsersRepoInterface, self).__init__(service, repo_name)
        self.db_name_suffix = self.service.config.get('users_db')
        self.users_db = self.db(db_name_suffix=self.db_name_suffix, db_type="users_db")

    def initialize(self):
        initial_users = self.service.config["initial_users"]
        self.users_db.add_index(keys_dict={
            "authentication_infos.auth_user_id": 1
        }, index_name="authentication_infos.auth_user_id")

        # Add initial users to the users db if they don't exist.
        logging.info("Add initial users to the users db if they don't exist.")
        if initial_users is None:
            return
        for initial_user_dict in initial_users:
            initial_user = User.make_from_dict(initial_user_dict)
            matching_users = self.users_db.get_matching_users_by_auth_infos(user=initial_user)
            if len(matching_users) == 0:
                logging.info("Adding: " + str(initial_user))
                # Use this instead of update_doc to auto-generate auth_secret_bcrypt
                initial_user.update_collection(db_interface=self.users_db)
            else:
                logging.info("Not adding: " + str(initial_user))

    def reset(self):
        self.store.delete_db(
            repo_name=self.repo_name,
            db_name_suffix=self.db_name_suffix)


class VedavaapiUsers(VedavaapiService):
    repo_interface_class = UsersRepoInterface
    dependency_services = ['store', 'credentials']

    def __init__(self, registry, name, conf):
        super(VedavaapiUsers, self).__init__(registry, name, conf)
        self.vvstore = registry.lookup("store")
        self.default_permissions = self.config["default_permissions"]
        import_blueprints_after_service_is_ready(self)

    def db(self, repo_name):
        return self.get_repo(repo_name).users_db

    def oauth_config(self, repo_name, provider_name):
        oauth_config = self.config['oauth']
        provider_specific_config = oauth_config.get(provider_name)
        provider_specific_config['client_secret_file_path'] = self.registry.lookup('credentials').creds_path(
            repo_name,
            provider_specific_config['client_secret_file_base_path'])
        return provider_specific_config


def myservice():
    return ServiceObj


def get_default_permissions():
    return myservice().default_permissions


api_blueprints = []


def import_blueprints_after_service_is_ready(service_obj):
    global ServiceObj
    ServiceObj = service_obj
    from .api import apiv0_blueprint, apiv1_blueprint
    api_blueprints.extend((apiv1_blueprint, apiv0_blueprint))
