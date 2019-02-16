import logging
import os

from vedavaapi.common import VedavaapiService, OrgHandler

from .helpers.bootstrap_helper import bootstrap_registry

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


class RegistryOrgHandler(OrgHandler):
    def __init__(self, service, org_name):
        super(RegistryOrgHandler, self).__init__(service, org_name)
        self.registry_db_config = self.dbs_config['registry_db']
        self.registry_db = self.store.db(db_name_suffix=self.registry_db_config['name'])

        self.registry_colln = self.registry_db.get_collection(self.registry_db_config['collections']['registry'])


    def initialize(self):
        self.registry_resource_id = bootstrap_registry(self.registry_colln, self.org_name)


class VedavaapiRegistry(VedavaapiService):
    instance = None
    org_handler_class = RegistryOrgHandler

    title = 'Vedavaapi Registry'
    description = 'Registry service.'

    def get_registry_colln(self, org_name):
        return self.get_org(org_name).registry_colln

    def get_registry_resource_id(self, org_name):
        return self.get_org(org_name).registry_resource_id

    def get_accounts_api_config(self, org_name):
        return self.get_org(org_name).accounts_api_config
