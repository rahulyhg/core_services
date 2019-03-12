import os

from flask import g
from vedavaapi.common.api_common import get_current_org

from . import myservice

def _get_token_resolver_endpoint():
    current_org_name = get_current_org()
    accounts_api_config = myservice().get_accounts_api_config(current_org_name)

    url_root = accounts_api_config.get('url_root', g.original_url_root)
    token_resolver_endpoint = os.path.join(
        url_root.lstrip('/'),
        current_org_name,
        'accounts/oauth/v1/resolve_token'
    )
    return token_resolver_endpoint


def push_environ_to_g():
    from flask import g
    g.current_org_name = get_current_org()
    g.token_resolver_endpoint = _get_token_resolver_endpoint()
