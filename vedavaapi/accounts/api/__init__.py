import functools

from authlib.specs.rfc6749 import MissingAuthorizationError, OAuth2Error
from flask import session, request
from vedavaapi.common.api_common import get_current_org
from vedavaapi.objectdb.mydb import MyDbCollection

from .. import VedavaapiAccounts
from ..oauth_server_helpers.authorization_server import AuthorizationServer


def myservice():
    instance = VedavaapiAccounts.instance  # type: VedavaapiAccounts
    return instance


def get_current_user_id():
    authentications = session.get('authentications', {})
    current_org_name = get_current_org()
    if not current_org_name in authentications:
        return None
    return authentications[current_org_name]['user_id']


def sign_out_user(org_name):
    if not session.get('authentications', None):
        return None
    authentications = session['authentications']
    if not authentications.get(org_name, None):
        return None
    return authentications.pop(org_name, None)


def get_users_colln():
    org_name = get_current_org()
    users_colln = myservice().get_users_colln(org_name)  # type: MyDbCollection
    return users_colln


def get_oauth_colln():
    org_name = get_current_org()
    oauth_colln = myservice().get_oauth_colln(org_name)  # type: MyDbCollection
    return oauth_colln


def get_authlib_authorization_server():
    org_name = get_current_org()
    authorization_server = myservice().get_authlib_authorization_server(org_name)  # type: AuthorizationServer
    return authorization_server


def get_authorizer_config():
    return myservice().get_authorizer_config()


def get_initial_agents():
    org_name = get_current_org()
    return myservice().get_initial_agents(org_name)


def require_oauth(scope=None, operator='AND', optional=False):

    def wrapper(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            # org_name = get_current_repo()
            resource_protector = myservice().get_resource_protector('vedavaapi')
            try:
                resource_protector.acquire_token(scope, operator)
            except MissingAuthorizationError as error:
                if optional:
                    return f(*args, **kwargs)
                resource_protector.raise_error_response(error)
            except OAuth2Error as error:
                resource_protector.raise_error_response(error)
            return f(*args, **kwargs)
        return decorated
    return wrapper


from .agents.v1 import api_blueprint_v1 as api_blueprint_agents_v1
from .oauth.v1 import api_blueprint_v1 as api_blueprint_oauth_v1

blueprints_path_map = {
    api_blueprint_agents_v1: "/agents/v1",
    api_blueprint_oauth_v1: "/oauth/v1"
}
