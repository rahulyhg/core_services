import json
import sys

import requests
from flask import request, session
import flask
from sanskrit_ld.schema import JsonObject
from vedavaapi.common import VedavaapiServices
from vedavaapi.accounts import VedavaapiAccounts


def get_current_org():
    org_name = request.environ['SCRIPT_NAME'].split('/')[-1]
    if not org_name:
        error = error_response(message='resource not found', code=404)
        abort_with_error_response(error)
    if org_name not in flask.current_app.config.get('ORGS', {}):
        error = error_response(message='resource not found', code=404)
        abort_with_error_response(error)
    return org_name


def get_current_user_id(required=False):
    authentications = session.get('authentications', {})
    current_org_name = get_current_org()
    if current_org_name not in authentications:
        if required:
            error = error_response(message='not authorized', code=401)
            abort_with_error_response(error)
        return None
    return authentications[current_org_name]["user_id"]

def get_current_user_group_ids():
    current_user_id = get_current_user_id()
    return get_group_ids(get_current_org(), current_user_id)

def get_group_ids(org_name, user_id):
    accounts_service = VedavaapiServices.lookup('accounts')  # type: VedavaapiAccounts
    users_colln = accounts_service.get_users_colln(org_name)

    group_ids = [
        group['_id'] for group in users_colln.find(
            {"jsonClass": "UsersGroup", "members": user_id}, projection={"_id": 1}
        )
    ]
    return group_ids


def get_user(org_name, user_id, projection=None, raise_if_not_exists=True):
    accounts_service = VedavaapiServices.lookup('accounts')  # type: VedavaapiAccounts
    users_colln = accounts_service.get_users_colln(org_name)
    if projection is not None:
        if 0 in projection.values():
            projection.pop('jsonClass', None)
        else:
            projection.update({"jsonClass": 1})

    user_json = users_colln.get(user_id, projection=projection)
    if raise_if_not_exists and user_json is None:
        error = error_response(message='invalid user', code=400)
        abort_with_error_response(error)

    return JsonObject.make_from_dict(user_json)


def get_initial_agents():
    current_org_name = get_current_org()
    accounts_service = VedavaapiServices.lookup('accounts')  # type: VedavaapiAccounts
    return accounts_service.get_initial_agents(current_org_name)


def jsonify_argument(doc_string, key=None):
    if doc_string is None:
        return None
    try:
        doc = json.loads(doc_string)
        return doc
    except json.JSONDecodeError:
        message = 'invalid json' + (' for {}'.format(key) if key is not None else '')
        error = error_response(message=message, code=400)
        abort_with_error_response(error)


def check_argument_type(obj, allowed_types, key=None, allow_none=False, respond_if_error=True):
    if obj is None:
        if allow_none:
            return True
        error = error_response(message='{} should be provided'.format(key or 'object'), code=400)
        abort_with_error_response(error)

    for t in allowed_types:
        if isinstance(obj, t):
            return True

    if not respond_if_error:
        return False

    message = '{}\'s type should be one among {}'.format(key or 'object', str(allowed_types))
    error = error_response(message=message, code=400)
    abort_with_error_response(error)


def get_authorization_token():
    if request.headers.get('Authorization', None):
        return request.headers['Authorization'], False

    elif session.get('authorization', None):
        authorization_cookie = session['authorization']
        print(authorization_cookie, file=sys.stderr)
        if not authorization_cookie.get('provider', None) == 'vedavaapi':
            return None, False
        if not authorization_cookie.get('authorization_token', None):
            return None, True
        return authorization_cookie['authorization_token'], True
    else:
        return None, False


def resolve_token(resolve_token_uri, include_user=False, required_scopes=None, operator='OR'):
    token, internal = get_authorization_token()
    if token is None:
        error = error_response(message='not authorized', code=401)
        abort_with_error_response(error)

    # noinspection PyUnboundLocalVariable
    token_info_response = requests.get(
        resolve_token_uri, headers={"Authorization": "Bearer " + token}, params={"include_user": include_user})
    if token_info_response.status_code != 200:
        error = error_response(
            message='invalid authorization', code=403, oauth_server_response=token_info_response.json())
        abort_with_error_response(error)
    token_info = token_info_response.json()

    granted_scopes = set(token_info['scopes'])
    required_scopes = set(required_scopes or [])

    if ((operator == 'AND' and not required_scopes.issubset(granted_scopes))
            or (operator == 'OR' and required_scopes.isdisjoint(granted_scopes))):
        error = error_response(message='client doesn\'t have authorization for this scope', code=403)
        abort_with_error_response(error)

    return token_info


def abort_with_error_response(response):
    flask.abort(response)


def error_response(**kwargs):
    # function to construct all types of error response jsons
    error = {
        'code': 500  # default if not provided
    }
    if 'inherited_error_response' in kwargs:
        inherited_error_response = kwargs['inherited_error_response']
        error['code'] = inherited_error_response['error'].get('code', 500)
    error.update(kwargs)
    response = flask.make_response(
        flask.jsonify(error),  # json
        error['code']  # code
    )
    return response
