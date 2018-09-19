import logging
import sys
import os

from sanskrit_data.schema.users import User
from vedavaapi.common import VedavaapiService

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

ServiceObj = None
DEFAULT_REPO = None


class VedavaapiUsers(VedavaapiService):
    config_template = {
        "users_db_name": "vedavaapi_users",
        "oauth": {
            "google": {
                "comment": "Created by vishvas.vasuki at https://console.developers.google.com/apis/credentials?project=sanskritnlp",
                "client_id": "703448017295-2rod58o21lumfs1jkhphaojkh46cooo1.apps.googleusercontent.com",
                "client_secret": "Ns2-dcnpEb5M84hdhtRvUaC0"
            },
            "facebook": {
                "client_id": "1706950096293019",
                "client_secret": "1b2523ac7d0f4b7a73c410b2ec82586c"
            },
            "twitter": {
                "client_id": "jSd7EMZFTQlxjLFG4WLmAe2OX",
                "client_secret": "gvkh9fbbnKQXXbnqxfs8C0tCEqgNKKzoYJAWQQwtMG07UOPKAj"
            }
        },
        "initial_users": [
            {
                "authentication_infos": [
                    {
                        "auth_provider": "google",
                        "auth_user_id": "sai.susarla@gmail.com",
                        "jsonClass": "AuthenticationInfo"
                    }
                ],
                "jsonClass": "User",
                "permissions": [
                    {
                        "actions": [
                            "read",
                            "write",
                            "admin"
                        ],
                        "jsonClass": "UserPermission",
                        "service": ".*"
                    }
                ],
                "user_type": "human"
            },
            {
                "authentication_infos": [
                    {
                        "auth_provider": "vedavaapi",
                        "auth_user_id": "vedavaapiAdmin",
                        "auth_secret_plain": "@utoDump1",
                        "jsonClass": "AuthenticationInfo"
                    }
                ],
                "jsonClass": "User",
                "permissions": [
                    {
                        "actions": [
                            "read",
                            "write",
                            "admin"
                        ],
                        "jsonClass": "UserPermission",
                        "service": ".*"
                    }
                ],
                "user_type": "bot"
            }
        ],
        "default_permissions": [
            {
                "actions": [
                    "read",
                    "write"
                ],
                "jsonClass": "UserPermission",
                "service": "quotes"
            }
        ]
    }

    dependency_services = ['store']

    def __init__(self, registry, name, conf):
        super(VedavaapiUsers, self).__init__(registry, name, conf)
        self.vvstore = registry.lookup("store")
        import_blueprints_after_service_is_ready(self)

    def reset(self, repos=None):
        db_name_end = self.config.get('users_db')
        self.vvstore.delete_db_in_repos(db_name_end=db_name_end, repos=repos)

    def setup(self, repos=None):
        if repos is None:
            repos = self.vvstore.all_repos()

        db_name_end = self.config.get('users_db')
        self.dbs_map = self.vvstore.db_interfaces_from_repos(
            db_name_end=db_name_end,
            db_name_frontend='users',
            db_type="users_db"
        )

        initial_users = self.config["initial_users"]
        default_permissions_in = self.config["default_permissions"]

        for repo, db_interface in self.dbs_map.items():
            if not repo in repos:
                continue
            db_interface.add_index(keys_dict={
                "authentication_infos.auth_user_id": 1
            }, index_name="authentication_infos.auth_user_id")

            # Add initial users to the users db if they don't exist.
            logging.info("Add initial users to the users db if they don't exist.")
            if initial_users is not None:
                for initial_user_dict in initial_users:
                    initial_user = User.make_from_dict(initial_user_dict)
                    matching_users = db_interface.get_matching_users_by_auth_infos(user=initial_user)
                    if len(matching_users) == 0:
                        logging.info("Adding: " + str(initial_user))
                        # Use this instead of update_doc to auto-generate auth_secret_bcrypt
                        initial_user.update_collection(db_interface=db_interface)
                    else:
                        logging.info("Not adding: " + str(initial_user))

        self.default_permissions = default_permissions_in

    def get_db(self, repo_id):
        return self.dbs_map.get(repo_id, None)


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
