import functools
import os

from flask import session, request, g
from vedavaapi.common.api_common import get_current_org
from vedavaapi.objectdb.mydb import MyDbCollection

from . import myservice
from ..oauth_server_helpers.authorization_server import AuthorizationServer


def _get_current_user_id():
    current_org_name = get_current_org()
    authentications = session.get('authentications', {})
    if current_org_name not in authentications:
        return None
    return authentications[current_org_name]['user_id']


def _get_users_colln():
    current_org_name = get_current_org()
    _users_colln = myservice().get_users_colln(current_org_name)  # type: MyDbCollection
    return _users_colln


def _get_oauth_colln():
    current_org_name = get_current_org()
    _oauth_colln = myservice().get_oauth_colln(current_org_name)  # type: MyDbCollection
    return _oauth_colln


def _get_authlib_authorization_server():
    current_org_name = get_current_org()
    _authorization_server = myservice().get_authlib_authorization_server(current_org_name)  # type: AuthorizationServer
    return _authorization_server


def _get_authorizer_config():
    return myservice().get_authorizer_config()


def _get_initial_agents():
    current_org_name = get_current_org()
    return myservice().get_initial_agents(current_org_name)


def _get_token_resolver_endpoint():
    current_org_name = get_current_org()

    url_root = g.original_url_root
    token_resolver_endpoint = os.path.join(
        url_root.lstrip('/'),
        current_org_name,
        'accounts/oauth/v1/resolve_token'
    )
    return token_resolver_endpoint


def push_environ_to_g():
    from flask import g
    g.users_colln = _get_users_colln()
    g.oauth_colln = _get_oauth_colln()
    g.authorization_server = _get_authlib_authorization_server()
    g.authorizer_config = _get_authorizer_config()
    g.current_org_name = get_current_org()
    g.current_user_id = _get_current_user_id()
    g.initial_agents = _get_initial_agents()
    g.token_resolver_endpoint = _get_token_resolver_endpoint()


def set_environ(func):
    @functools.wraps(func)
    def _with_environ(*args, **kwargs):
        push_environ_to_g()
        return func(*args, **kwargs)
    return _with_environ
