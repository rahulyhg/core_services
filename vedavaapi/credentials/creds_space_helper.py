import json
import os

from sanskrit_data.schema import common
from . import schema


class CredsSpaceHelper(object):
    creds_space_classes = {}

    def __init__(self, creds_dir):
        self.creds_dir = creds_dir

    @classmethod
    def register_creds_space_class(cls, creds_space_name, creds_space_class):
        cls.creds_space_classes[creds_space_name] = creds_space_class

    @classmethod
    def get_helper_for_creds_space(cls, credentials_service, creds_space_name):
        helper_class = cls.creds_space_classes.get(creds_space_name, None)
        if not helper_class:
            return None
        return helper_class(credentials_service)


class OauthSpace(CredsSpaceHelper):

    def __init__(self, creds_dir):
        super(OauthSpace, self).__init__(creds_dir)

    def credentials_path_for(self, provider, project=None, client=None, type=None, authorized=False, authorized_creds_file=None, scopes=None, fallback_if_not_exist=False, be_liberal=False):

        setup_file = "SETUP.json"
        provider_path = os.path.join(self.creds_dir, provider)
        # print('provider_path', provider_path)
        try:
            # determining appropriate provider, project_name
            provider_setup_dict = json.loads(open(os.path.join(provider_path, setup_file), 'rb').read().decode('utf-8'))
            provider_setup = common.JsonObject.make_from_dict(provider_setup_dict)
            project_name = provider_setup.get_project_name(project, fallback_if_not_exist=fallback_if_not_exist)
            if project_name is None:
                return None
            project_path = os.path.join(provider_path, project_name)
            # print('project_path', project_path)

            # determining appropriate client
            project_setup_dict = json.loads(open(os.path.join(project_path, setup_file), 'rb').read().decode('utf-8'))
            project_setup = common.JsonObject.make_from_dict(project_setup_dict)
            client_name = project_setup.get_client_name(client, type=type, authorized=authorized, fallback_if_not_exist=fallback_if_not_exist, be_liberal=be_liberal)
            if client_name is None:
                return None
            client_path = os.path.join(project_path, client_name)
            client_folder_list = os.listdir(client_path)

            if not authorized:
                if not 'client_secret.json' in client_folder_list:
                    return None
                else:
                    return os.path.join(client_path, 'client_secret.json')

            authorized_setup_dict = json.loads(open(os.path.join(client_path, 'authorized', setup_file), 'rb').read().decode('utf-8'))
            authorized_setup = common.JsonObject.make_from_dict(authorized_setup_dict)
            return authorized_setup.get_authorized_creds_file(authorized_creds_file, scopes, fallback_if_not_exist)

        except FileNotFoundError as e:
            raise e
            #return None

