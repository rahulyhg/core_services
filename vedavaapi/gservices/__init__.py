import os.path

from vedavaapi.common import VedavaapiService

from vedavaapi.google_helper import GServices

ServiceObj = None

class VedavaapiGservices(VedavaapiService):
    config_template = {
      "google_creds_base_dir" : "/home/samskritam/vedavaapi/core_services/vedavaapi/conf_local/creds/google/",
      "credentials_path" : "vedavaapi-credentials.json",
      "is_service_account_credentials" : 0,
      "scopes" : [
        "https://www.googleapis.com/auth/drive.readonly", 
        "https://www.googleapis.com/auth/spreadsheets.readonly"]
    }

    def __init__(self, registry, name, conf):
        super(VedavaapiGservices, self).__init__(registry, name, conf)
        global ServiceObj
        ServiceObj = self

    def services(self, custom_conf=None):
        """
        this takes an optional custom configuration dictionary,
        And returns GServices helper objects for that config.
        if custom config didn't have any specialized configuration for 'credentials_path', or 'scopes', etc, then it will uses global vedavaapi configuration from 'gservices' dict key in config file.

        :param custom_conf: custom configuration dictionary. if it is not provided, then by default global config will be used.
        """
        custom_conf = custom_conf if custom_conf is not None else {}
        effective_conf = self.config.copy()
        effective_conf.update(custom_conf)
        '''
        callee_vedavaapi_service = self.registry.lookup(vedavaapi_service_name)

        if callee_vedavaapi_service is not None:
            callee_config = callee_vedavaapi_service.config
            effective_conf.update(callee_config)
        '''

        creds_dir = effective_conf['google_creds_base_dir']
        credentials_relative_path = effective_conf['credentials_path']
        credentials_path = os.path.join(creds_dir, credentials_relative_path)
        scopes = effective_conf['scopes']
        auth_through_service_account = bool(effective_conf['is_service_account_credentials'])

        return GServices.from_creds_file(credentials_path, scopes=scopes, auth_through_service_account=auth_through_service_account)

def myservice():
    return ServiceObj
