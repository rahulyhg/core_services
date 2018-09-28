import sys

from sanskrit_data.schema import common


class AuthorizedCredsMeta(common.JsonObject):
    schema = common.recursively_merge_json_schemas(common.JsonObject.schema, {
        "type": "object",
        "properties": {
            common.TYPE_FIELD: {
                "enum": ["AuthorizedCredsMeta"]
            },
            "scopes": {
                "type": "array",
                "items": "string",
                "minItems": 1
            }
        },
        "required": ["scopes"]
    })

    @classmethod
    def from_details(cls, scopes):
        obj = cls()
        obj.scopes = scopes
        return obj


class ApiClientMeta(common.JsonObject):
    schema = common.recursively_merge_json_schemas(common.JsonObject.schema, {
        "type": "object",
        "properties": {
            common.TYPE_FIELD: {
                "enum": ["ApiClientMeta"]
            },
            "client_type": {
                "type": "string",
            }
        },
        "required": ["client_type"]
    })

    @classmethod
    def from_details(cls, client_type):
        obj = cls()
        obj.client_type = client_type
        return obj

class ApiProjectMeta(common.JsonObject):
    schema = common.recursively_merge_json_schemas(common.JsonObject.schema, {
        "type": "object",
        "properties": {
            common.TYPE_FIELD: {
                "enum": ["ApiProjectMeta"]
            }
        }
    })

    @classmethod
    def from_details(cls):
        return cls()


class AuthorizedCredsSetup(common.JsonObject):
    schema = common.recursively_merge_json_schemas(common.JsonObject.schema, {
        "type": "object",
        "properties": {
            common.TYPE_FIELD: {
                "enum": ["AuthorizedCredsSetup"]
            },
            "authorized_creds_files": {
                "type": "object",
                "additionalProperties": AuthorizedCredsMeta.schema
            }
        },
        "default_authorized_creds_file": {
            "type": "string"
        }
    })

    @classmethod
    def from_details(cls, authorized_creds_files=None, default_authorized_creds_file=None):
        obj = cls()
        if authorized_creds_files:
            obj.authorized_creds_files= authorized_creds_files
        if default_authorized_creds_file:
            obj.default_authorized_creds_file= default_authorized_creds_file
        return obj

    # noinspection PyUnresolvedReferences
    def get_authorized_creds_file(self, authorized_creds_file=None, scopes=None, fallback_if_not_exist=False, resolve_defaults=True):
        if not hasattr(self, 'authorized_creds_files'):
            return None
        if authorized_creds_file is not None:
            if not hasattr(self.authorized_creds_files, authorized_creds_file):
                if not fallback_if_not_exist:
                    return None
            else:
                return authorized_creds_file

        if not resolve_defaults:
            return None
        if scopes is not None:
            cred_files_dict = self.to_json_map()['authorized_creds_files']
            profiles = {}
            for key, value in cred_files_dict.items():
                if not False in [scope in value.scopes for scope in scopes]:
                    return key
            return None

        if hasattr(self, 'default_authorized_creds_file'):
            return self.default_authorized_creds_file

        return None


class ApiProjectSetup(common.JsonObject):
    schema = common.recursively_merge_json_schemas(common.JsonObject.schema, {
        "type": "object",
        "properties": {
            common.TYPE_FIELD: {
                "enum": ["ApiProjectSetup"]
            },
            "clients": {
                "type": "object",
                "additionalProperties": ApiClientMeta.schema
            },
            "default_client": {
                "type": "string"
            },

            "default_installed_client": {
                "type": "string"
            },
            "default_web_client": {
                "type": "string"
            },
            "default_service_client": {
                "type": "string"
            },
            "default_authorized_client": {
                "type": "string"
            }
        }
    })

    @classmethod
    def from_details(cls, clients, defaults=None):
        if defaults is None:
            defaults= {}
        obj = cls()
        obj.clients = clients
        for key, value in defaults.items():
            setattr(obj, key, value)
        return obj

    # noinspection PyUnresolvedReferences
    def get_client_name(self, client=None, type=None, authorized=False, resolve_defaults=True, fallback_if_not_exist=False, be_liberal=False):
        if not hasattr(self, 'clients'):
            print(1)
            return None
        if client is not None:
            if not hasattr(self.clients, client):
                if not fallback_if_not_exist:
                    print(2)
                    return None
            else:
                return client

        if not resolve_defaults:
            print(3)
            return None
        if type is not None:
            try:
                return self.__getattribute__('default_{}_client'.format(type))
            except AttributeError as ae:
                print(4)
                return None
        if authorized:
            try:
                return self.__getattribute__('default_{}_client'.format('authorized'))
            except AttributeError as ae:
                if not be_liberal:
                    print(5)
                    return None

        try:
            return self.__getattribute__('default_client')
        except AttributeError as ae:
            print(6)
            return None


class OauthProviderSetup(common.JsonObject):
    schema = common.recursively_merge_json_schemas(common.JsonObject.schema, {
        "type": "object",
        "properties": {
            common.TYPE_FIELD: {
                "enum": ["ApiProjectSetup"]
            },
            "projects": {
                "type": "object",
                "additionalProperties": ApiProjectMeta.schema
            },
            "default_project": {
                "type": "string"
            }
        }
    })

    @classmethod
    def from_details(cls, projects, defaults=None):
        if defaults is None:
            defaults = {}

        obj = cls()
        obj.projects = projects
        for key, value in defaults.items():
            setattr(obj, key, value)
        return obj

    # noinspection PyUnresolvedReferences
    def get_project_name(self, project=None, fallback_if_not_exist=False, resolve_defaults=True):
        if not hasattr(self, 'projects'):
            return None
        if project is not None:
         if not hasattr(self.projects, project):
            if not fallback_if_not_exist:
                return None
         else:
             return project

        if not resolve_defaults:
            return None
        if not hasattr(self, 'default_project'):
            return None

        return self.default_project

common.update_json_class_index(sys.modules[__name__])

