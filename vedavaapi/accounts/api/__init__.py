import functools

from authlib.specs.rfc6749 import MissingAuthorizationError, OAuth2Error
from flask import session
from vedavaapi.common.helpers.api_helper import get_current_org

from .. import VedavaapiAccounts


def myservice():
    instance = VedavaapiAccounts.instance  # type: VedavaapiAccounts
    return instance


def sign_out_user(org_name):
    if not session.get('authentications', None):
        return None
    if org_name not in session['authentications']:
        return None
    authentication = session['authentications'].pop(org_name)
    session.modified = True
    return authentication


def require_oauth(scope=None, operator='AND', optional=False):

    def wrapper(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            resource_protector = myservice().get_resource_protector(get_current_org())
            try:
                resource_protector.acquire_token(scope, operator)
            except MissingAuthorizationError as error:
                print(error)
                if optional:
                    return f(*args, **kwargs)
                resource_protector.raise_error_response(error)
            except OAuth2Error as error:
                print(error)
                resource_protector.raise_error_response(error)
            return f(*args, **kwargs)
        return decorated
    return wrapper


from . import environ

from .agents.v1 import api_blueprint_v1 as api_blueprint_agents_v1
from .oauth.v1 import api_blueprint_v1 as api_blueprint_oauth_v1

api_blueprint_agents_v1.before_request(environ.push_environ_to_g)
api_blueprint_oauth_v1.before_request(environ.push_environ_to_g)

blueprints_path_map = {
    api_blueprint_agents_v1: "/agents/v1",
    api_blueprint_oauth_v1: "/oauth/v1"
}
