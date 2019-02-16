import logging
import os

from authlib.flask.oauth2 import ResourceProtector
from vedavaapi.common import VedavaapiService, OrgHandler

from .agents_helpers import bootstrap_helper, users_helper
from .oauth_server_helpers.authorization_server import AuthorizationServer
from .oauth_server_helpers.models import create_bearer_token_validator


logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


class AccountsOrgHandler(OrgHandler):
    def __init__(self, service, org_name):
        super(AccountsOrgHandler, self).__init__(service, org_name)
        self.users_db_config = self.dbs_config['users_db']
        self.users_db = self.store.db(db_name_suffix=self.users_db_config['name'])

        self.users_colln = self.users_db.get_collection(self.users_db_config['collections']['users'])
        self.oauth_colln = self.users_db.get_collection(self.users_db_config['collections']['oauth'])

        self.authlib_config = self.service.config['authlib']
        self.authlib_authorization_server = AuthorizationServer(self.authlib_config, self.oauth_colln, self.users_colln)

        bearer_validator = create_bearer_token_validator(self.oauth_colln)
        self.resource_protector = ResourceProtector()
        self.resource_protector.register_token_validator(bearer_validator())

    def initialize(self):
        self.users_colln.create_index(keys_dict={
            "email": 1
        }, index_name="email")

        initial_agents_config = self.service.config["initial_agents"].copy()
        initial_agents_config['users']['root_admin'].update(self.org_config['root_admin'])

        logging.info("Add initial agents to the users db if they don't exist.")
        if initial_agents_config is None:
            return
        self.initial_agents = bootstrap_helper.bootstrap_initial_agents(
            self.users_colln, self.oauth_colln, initial_agents_config
        )


class VedavaapiAccounts(VedavaapiService):
    instance = None
    org_handler_class = AccountsOrgHandler
    dependency_services = ['credentials']

    title = 'Vedavaapi Accounts'
    description = 'Service managing users, oauth authorization etc.'

    def __init__(self, registry, name, conf):
        super(VedavaapiAccounts, self).__init__(registry, name, conf)
        os.environ['AUTHLIB_INSECURE_TRANSPORT'] = self.config.get(
            'authlib', {}).get('AUTHLIB_INSECURE_TRANSPORT', '0')

    def get_users_colln(self, org_name):
        return self.get_org(org_name).users_colln

    def get_oauth_colln(self, org_name):
        return self.get_org(org_name).oauth_colln

    def get_authlib_authorization_server(self, org_name):
        return self.get_org(org_name).authlib_authorization_server

    def get_authorizer_config(self):
        return self.config.get('authorizer', {})

    def get_resource_protector(self, org_name):
        return self.get_org(org_name).resource_protector

    def get_initial_agents(self, org_name):
        initial_agents = self.get_org(org_name).initial_agents  # type: bootstrap_helper.InitialAgents
        return initial_agents

    def get_external_oauth_clients_config(self, org_name, provider_name):
        oauth_config = self.config['external_oauth_clients']
        provider_specific_config = oauth_config.get(provider_name, {})
        provider_specific_config['client_secret_file_path'] = self.registry.lookup('credentials').creds_path(
            org_name, 'oauth', provider_name, file_name=provider_specific_config.get('file_name', None))
        print('psoc', provider_specific_config)
        return provider_specific_config
