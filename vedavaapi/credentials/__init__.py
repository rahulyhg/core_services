import os

from vedavaapi.common import VedavaapiService, ServiceRepoInterface


class CredentialsRepoInterface(ServiceRepoInterface):

    def __init__(self, service, repo_name):
        super(CredentialsRepoInterface, self).__init__(service, repo_name)


class VedavaapiCredentials(VedavaapiService):
    # service to manage all sorts of credentials, oauth, or else.
    repo_interface_class = CredentialsRepoInterface
    dependency_services = ['store']

    def __init__(self, registry, name, conf):
        super(VedavaapiCredentials, self).__init__(registry, name, conf)
        self.store = registry.lookup('store')

    def creds_path(self, repo_name, creds_base_path, fallback_on_global=True):
        repo_specific_creds_path = self.get_repo(repo_name).file_store_path(
            'creds',
            creds_base_path
        )
        if os.path.exists(repo_specific_creds_path):
            return repo_specific_creds_path

        if fallback_on_global:
            global_creds_path = os.path.join(self.registry.mount_path, 'creds', creds_base_path)  # fallback on global
            if os.path.exists(global_creds_path):
                return global_creds_path

        return None

    #  def creds_for(self, ):
