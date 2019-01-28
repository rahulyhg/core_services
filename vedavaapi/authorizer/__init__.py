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
    description = 'convinience service for managing internal oauth tokens.'

    def __init__(self, registry, name, conf):
        super(VedavaapiAuthorizer, self).__init__(registry, name, conf)

    def get_oauth_config(self, org_name, provider_name):
        oauth_config = self.config['external_oauth_clients']
        provider_specific_config = oauth_config.get(provider_name, {})
        provider_specific_config['client_secret_file_path'] = self.registry.lookup('credentials').creds_path(
            org_name, 'oauth', provider_name, file_name=provider_specific_config.get('file_name', None))
        return provider_specific_config
