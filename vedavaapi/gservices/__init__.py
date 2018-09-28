import json

from vedavaapi.common import VedavaapiService, ServiceRepoInterface
from vedavaapi.google_helper import GServices


ServiceObj = None


def load_creds_config(creds_path):
    if creds_path is None:
        return None
    try:
        creds = json.loads(open(creds_path, 'rb').read().decode('utf-8'))
        auth_through_service_account = (creds.get('type', None) == 'service_account')
        scopes = creds['scopes'] if not auth_through_service_account else VedavaapiGservices.service_account_default_scopes
        return {
            'creds_path': creds_path,
            'auth_through_service_account': auth_through_service_account,
            'scopes': scopes
        }
    except FileNotFoundError:
        return None


class GservicesRepoInterface(ServiceRepoInterface):

    def __init__(self, service, repo_name):
        super(GservicesRepoInterface, self).__init__(service, repo_name)
        self.authorized_creds_path = self.service.registry.lookup('credentials').creds_path(
            repo_name=repo_name,
            creds_base_path=self.service.config['authorized_creds_base_path'])
        self.creds_config = load_creds_config(self.authorized_creds_path)

    def services(self):
        if not hasattr(self, 'gservices_object'):
            if self.creds_config is None:
                return None
            self.gservices_object = GServices.from_creds_file(**self.creds_config)
        return self.gservices_object


class VedavaapiGservices(VedavaapiService):
    service_account_default_scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly"]
    dependency_services = ['store', 'credentials']
    repo_interface_class = GservicesRepoInterface

    def __init__(self, registry, name, conf):
        super(VedavaapiGservices, self).__init__(registry, name, conf)
        import_blueprints_after_service_is_ready(self)

    def creds_path(self, repo_name):
        # to be used by it's api
        return self.get_repo(repo_name).authorized_creds_path

    def services(self, repo_name, custom_conf=None):
        repo = self.get_repo(repo_name)
        if custom_conf is None:
            return self.get_repo(repo_name).services()

        effective_conf = load_creds_config(repo.authorized_creds_path)
        effective_conf.update(custom_conf)
        return GServices.from_creds_file(**effective_conf)


def myservice():
    return ServiceObj


api_blueprints = []


def import_blueprints_after_service_is_ready(service_obj):
    global ServiceObj
    ServiceObj = service_obj
    from .api import v1_bp
    api_blueprints.append(v1_bp)
