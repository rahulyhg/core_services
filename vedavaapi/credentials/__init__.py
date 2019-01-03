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
    description = 'service to manage all sorts of credentials, and facilitate easy access to them, for other vedavaapi services'

    def __init__(self, registry, name, conf):
        super(VedavaapiCredentials, self).__init__(registry, name, conf)

    def creds_path(self, org_name, creds_base_path, fallback_on_global=True):
        if org_name is not None:
            repo_specific_creds_path = self.get_org(org_name).store.file_store_path(
                'creds',
                creds_base_path
            )
            if os.path.exists(repo_specific_creds_path):
                return repo_specific_creds_path

        if fallback_on_global:
            global_creds_path = os.path.join(self.registry.install_path, 'creds', creds_base_path)  # fallback on global
            if os.path.exists(global_creds_path):
                return global_creds_path

        return None

    #  def creds_for(self, ):
