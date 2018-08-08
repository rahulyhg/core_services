import os.path

from vedavaapi.common import VedavaapiService

from vedavaapi.google_helper.oauth import creds_helper
import vedavaapi.google_helper.gsheets.helper as gsheets_helper
import vedavaapi.google_helper.gdrive.helper as gdrive_helper

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

    def services(self, vedavaapi_service_name=None):
        """
        this takes name of vedavaapi service name, like(sling, smaps, etc.)
        And returns GServices helper objects for them according to their configuration dict in config.
        if they didn't have any specialized configuration for 'credentials_path', or 'scopes', etc, then it will uses global vedavaapi configuration from 'gservices' dict key in config file.

        :param vedavaapi_service_name: name of vedavaapi service. if it is not provided, the by default global config will be used.
        """
        effective_conf = self.config.copy()
        callee_vedavaapi_service = self.registry.lookup(vedavaapi_service_name)

        if callee_vedavaapi_service is not None:
            callee_config = callee_vedavaapi_service.config
            effective_conf.update(callee_config)

        creds_dir = effective_conf['google_creds_base_dir']
        credentials_relative_path = effective_conf['credentials_path']
        credentials_path = os.path.join(creds_dir, credentials_relative_path)
        scopes = effective_conf['scopes']
        auth_through_service_account = bool(effective_conf['is_service_account_credentials'])

        return GServices(credentials_path, scopes=scopes, auth_through_service_account=auth_through_service_account)

def myservice():
    return ServiceObj

class GServices(object):

    def __init__(self, credentials_path, scopes, auth_through_service_account=False):
        '''

        :param credentials_path: path to credentials file
        :param scopes: scopes to be enabled
        :param auth_through_service_account: are credentials are of service_account?
        '''
        self.__services = {}
        self.__credentials = creds_helper.credentials_from_file(credentials_path, scopes, auth_through_service_account=auth_through_service_account)


    def __init_gdrive(self, force=False, **kwargs):
        if 'drive' in self.__services and self.__services.get('drive', None) is not None:
            if not force:
                return

        try:
            gdrive_discovery_service = gdrive_helper.build_service(self.__credentials)
        except:
            raise
        if gdrive_discovery_service is None:
            raise RuntimeError('cannot instantiate gdrive_discovery_service')
        self.__services['drive'] = gdrive_helper.GDrive(gdrive_discovery_service, **kwargs)


    def __init_gsheets(self, force=False, enable_drive_service_linking=False, **kwargs):
        if 'sheets' in self.__services and self.__services.get('sheets', None) is not None:
            if not force:
                return

        if enable_drive_service_linking:
            self.__init_gdrive(force=False, **kwargs)

        try:
            gsheets_discovery_service = gsheets_helper.build_service(self.__credentials)
        except:
            raise
        if gsheets_discovery_service is None:
            raise RuntimeError('cannot instantiate gsheets_discovery_service')
        self.__services['sheets'] = gsheets_helper.GSheets(gsheets_discovery_service, drive_service=self.__services.get("drive", None), **kwargs) if enable_drive_service_linking else gsheets_helper.GSheets(gsheets_discovery_service, **kwargs)


    def gdrive(self, refresh=False, **kwargs):
        self.__init_gdrive(force=refresh, **kwargs)
        return self.__services['drive']


    def gsheets(self, refresh=False, enable_drive_service_linking=False, **kwargs):
        self.__init_gsheets(force=refresh, enable_drive_service_linking=enable_drive_service_linking, **kwargs)
        return self.__services['sheets']
