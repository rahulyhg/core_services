import functools
import sys

import requests
# noinspection PyProtectedMember
from flask import request, g, _app_ctx_stack
from requests import HTTPError
from werkzeug.local import LocalProxy

from .api_common import error_response, abort_with_error_response


class TokenInfo(object):

    def __init__(
            self, access_token=None, client_id=None,
            user_id=None, group_ids=None, scopes=None, scopes_satisfied=None):

        self.access_token = access_token
        self.client_id = client_id
        self.user_id = user_id
        self.group_ids = group_ids
        self.scopes = scopes
        self.scopes_satisfied = scopes_satisfied

    def set_from_dict(self, d):
        for key in d:
            if d[key] is None:
                continue
            setattr(self, key, d[key])


def check_scopes(required_scopes_structure, granted_scopes_set, major_operator):
    if required_scopes_structure is None:
        return True
    if granted_scopes_set is None:
        return False

    if major_operator == 'OR':
        for and_set in required_scopes_structure:
            if False not in [scope in granted_scopes_set for scope in and_set]:
                return True
        return False
    elif major_operator == 'AND':
        for or_set in required_scopes_structure:
            if True not in [scope in granted_scopes_set for scope in or_set]:
                return False
        return True
    else:
        return False


def resolve_token(
        token_resolver_uri, token_required=True,
        required_scopes_structure=None, major_operator='OR', abort_if_scopes_not_satisfied=True):

    ctx = _app_ctx_stack.top
    authorization_header = request.headers.get('Authorization', None)
    if authorization_header is None:
        if token_required:
            error = error_response(message='not authorized', code=401)
            abort_with_error_response(error)
        else:
            ctx.token_info = TokenInfo()
            return

    token_response = requests.get(token_resolver_uri, headers={"Authorization": authorization_header})
    try:
        token_response.raise_for_status()
    except HTTPError:
        error = error_response(message='invalid authorization', code=403)
        abort_with_error_response(error)
    token_json = token_response.json()

    token_info = TokenInfo(
        access_token=token_json.get('access_token'), user_id=token_json.get('user_id', None),
        client_id=token_json.get('client_id'), group_ids=token_json.get('group_ids', [])
    )
    ctx.token_info = token_info

    granted_scope = token_json.get('scope', None)
    if granted_scope is not None:
        token_info.scopes = granted_scope.split()

    if required_scopes_structure is None or token_info.user_id is None:
        token_info.scopes_satisfied = True
        return

    token_info.scopes_satisfied = check_scopes(
        required_scopes_structure, token_info.scopes, major_operator)

    if not token_info.scopes_satisfied and abort_if_scopes_not_satisfied:
        error = error_response(message='client doesn\'t have access to certain scopes')
        abort_with_error_response(error)


def require_oauth(
        token_resolver_endpoint=None, token_required=True,
        required_scopes_structure=None, major_operator='OR', abort_if_scopes_not_satisfied=True):

    def wrapper(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            resolve_token(
                token_resolver_endpoint or g.token_resolver_endpoint, token_required=token_required,
                required_scopes_structure=required_scopes_structure, major_operator=major_operator,
                abort_if_scopes_not_satisfied=abort_if_scopes_not_satisfied
            )
            return func(*args, **kwargs)
        return decorated
    return wrapper


def just_get_token_string(token_required=True):
    ctx = _app_ctx_stack.top
    authorization_header = request.headers.get('Authorization', None)
    if authorization_header is None:
        if token_required:
            error = error_response(message='not authorized', code=401)
            abort_with_error_response(error)
        else:
            ctx.current_token_string = None
            return
    try:
        token_type, access_token = authorization_header.split()
        if token_type.upper() != 'BEARER':
            error = error_response(message='invalid authorization', code=401)
            abort_with_error_response(error)
        ctx.current_token_string = access_token

    except ValueError:
        error = error_response(message='invalid authorization', code=401)
        abort_with_error_response(error)


def require_token_string(token_required=True):

    def wrapper(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            just_get_token_string(token_required=token_required)
            return func(*args, **kwargs)
        return decorated
    return wrapper


def _get_current_token():
    ctx = _app_ctx_stack.top
    return getattr(ctx, 'token_info', TokenInfo())


def _get_current_token_string():
    ctx = _app_ctx_stack.top
    return getattr(ctx, 'current_token_string', None)


current_token = LocalProxy(_get_current_token)
current_token_string = LocalProxy(_get_current_token_string)
