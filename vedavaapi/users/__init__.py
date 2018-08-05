import logging
import sys
import os

sys.path.append("..")
from sanskrit_data.schema.users import User
from vedavaapi.common import *

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

ServiceObj = None

class VedavaapiUsers(VedavaapiService):
    def __init__(self, name, conf):
        super(VedavaapiUsers, self).__init__(name, conf)
        self.vvstore = VedavaapiServices.lookup("store")
        global ServiceObj
        ServiceObj = self

    def reset(self):
        logging.info("Deleting database/collection " + self.config["users_db_name"])
        self.vvstore.client.delete_database(self.config["users_db_name"])

    def setup(self):
        self.users_db=self.vvstore.client.get_database_interface(
                        db_name_backend=self.config["users_db_name"],
                        db_name_frontend="users", 
                        db_type="users_db")

        initial_users=self.config["initial_users"]
        default_permissions_in=self.config["default_permissions"]

        self.users_db.add_index(keys_dict={
            "authentication_infos.auth_user_id": 1
        }, index_name="authentication_infos.auth_user_id")

        # Add initial users to the users db if they don't exist.
        logging.info("Add initial users to the users db if they don't exist.")
        if initial_users is not None:
            for initial_user_dict in initial_users:
                initial_user = User.make_from_dict(initial_user_dict)
                matching_users = self.users_db.get_matching_users_by_auth_infos(user=initial_user)
                if len(matching_users) == 0:
                    logging.info("Adding: " + str(initial_user))
                    # Use this instead of update_doc to auto-generate auth_secret_bcrypt
                    initial_user.update_collection(db_interface=self.users_db)
                else:
                    logging.info("Not adding: " + str(initial_user))

        self.default_permissions = default_permissions_in

# Directly accessing the module variable seems to yield spurious None values.
def get_service():
    return ServiceObj

def get_db():
  return get_service().users_db

def get_default_permissions():
  return get_service().default_permissions

from .api_v1 import api_blueprint as apiv1_blueprint

api_blueprints = [apiv1_blueprint]
