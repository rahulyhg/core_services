import json

from vedavaapi.common import VedavaapiService, OrgHandler
from vedavaapi.google_helper import GServices


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


class GservicesOrgHandler(OrgHandler):

    def __init__(self, service, org_name):
        super(GservicesOrgHandler, self).__init__(service, org_name)
        self.authorized_creds_path = self.service.registry.lookup('credentials').creds_path(
            org_name=org_name,
            creds_base_path=self.service.config['authorized_creds_base_path']
        )
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

    instance = None  # setting again to not fallback on super's

    dependency_services = ['credentials']
    org_handler_class = GservicesOrgHandler

    title = 'Vedavaapi Gservices'
    description = 'vedavaapi service, for easy interaction with all google api services.'

    def __init__(self, registry, name, conf):
        super(VedavaapiGservices, self).__init__(registry, name, conf)

    def creds_path(self, org_name):
        # to be used by it's api
        if org_name is not None:
            return self.get_org(org_name).authorized_creds_path
        else:
            return self.registry.lookup('credentials').creds_path(
                org_name=None,  # for fallback creds
                creds_base_path=self.config['authorized_creds_base_path']
            )

    def services(self, org_name, custom_conf=None):
        if org_name is not None:
            if custom_conf is None:
                return self.get_org(org_name).services()

        effective_conf = load_creds_config(self.creds_path(org_name=org_name))
        if custom_conf is not None:
            effective_conf.update(custom_conf)
        return GServices.from_creds_file(**effective_conf)
