import os

from vedavaapi.common import VedavaapiService, OrgHandler


class CredentialsOrgHandler(OrgHandler):

    def __init__(self, service, org_name):
        super(CredentialsOrgHandler, self).__init__(service, org_name)


class VedavaapiCredentials(VedavaapiService):
    # service to manage all sorts of credentials, oauth, or else.
    instance = None

    org_handler_class = CredentialsOrgHandler
    dependency_services = []

    title = 'VedavaapiCredentials'
    description = 'service to manage credentials'

    def __init__(self, registry, name, conf):
        super(VedavaapiCredentials, self).__init__(registry, name, conf)

    def creds_path(self, org_name, creds_type, provider_name, client_name='default.json', fallback_on_global=True):
        if client_name is None:
            client_name = 'default'
        file_name = '{}.json'.format(client_name)
        if org_name is not None:
            org_specific_creds_path = self.get_org(org_name).store.file_store_path(
                'creds',
                os.path.join(creds_type, provider_name, file_name)
            )
            if os.path.exists(org_specific_creds_path):
                return org_specific_creds_path
        if fallback_on_global:
            global_creds_path = os.path.join(
                self.registry.install_path, '_creds',
                creds_type, provider_name, file_name
            )
            if os.path.exists(global_creds_path):
                return global_creds_path
        return None
