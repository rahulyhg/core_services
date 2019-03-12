import logging

from vedavaapi.common import VedavaapiService, OrgHandler


logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


class AuthorizerOrgHandler(OrgHandler):
    pass


class VedavaapiAuthorizer(VedavaapiService):
    instance = None
    svc_repo_class = AuthorizerOrgHandler
    dependency_services = ['credentials']

    title = 'Vedavaapi Authorizer'
    description = 'Authorization central endpoint.'

    def __init__(self, registry, name, conf):
        super(VedavaapiAuthorizer, self).__init__(registry, name, conf)

    def get_oauth_client_config(self, org_name, provider_name, client_name=None):
        oauth_client_config = {}
        oauth_client_config['client_secret_file_path'] = self.registry.lookup('credentials').creds_path(
            org_name, 'oauth', provider_name, client_name=client_name)
        return oauth_client_config

    def get_accounts_api_config(self, org_name):
        return self.get_org(org_name).accounts_api_config
