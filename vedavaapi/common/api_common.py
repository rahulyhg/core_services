import json

import flask
from flask import request
from sanskrit_ld.schema import JsonObject


def get_current_org():
    org_name = request.environ['SCRIPT_NAME'].split('/')[-1]
    org_names_list = flask.current_app.config.get('ORGS', [])

    if not org_name or request.environ['ORIGINAL_SCRIPT_NAME'] == request.environ['SCRIPT_NAME']:
        if len(org_names_list) == 1:
            return org_names_list[0]
        else:
            error = error_response(message='resource not found', code=404)
            abort_with_error_response(error)

    if org_name not in flask.current_app.config.get('ORGS', []):
        error = error_response(message='resource not found', code=404)
        abort_with_error_response(error)
    return org_name


def get_initial_agents(org_name=None):
    from vedavaapi.common import VedavaapiServices
    from vedavaapi.accounts import VedavaapiAccounts
    if not org_name:
        org_name = get_current_org()
    accounts_service = VedavaapiServices.lookup('accounts')  # type: VedavaapiAccounts
    return accounts_service.get_initial_agents(org_name)


def get_user(org_name, user_id, projection=None):
    from vedavaapi.common import VedavaapiServices
    from vedavaapi.accounts import VedavaapiAccounts
    accounts_service = VedavaapiServices.lookup('accounts')  # type: VedavaapiAccounts
    users_colln = accounts_service.get_users_colln(org_name)
    if projection is not None:
        if 0 in projection.values():
            projection.pop('jsonClass', None)
        else:
            projection.update({"jsonClass": 1})

    user_json = users_colln.get(user_id, projection=projection)

    return JsonObject.make_from_dict(user_json)


def get_group(org_name, group_id, projection=None):
    from vedavaapi.common import VedavaapiServices
    from vedavaapi.accounts import VedavaapiAccounts
    accounts_service = VedavaapiServices.lookup('accounts')  # type: VedavaapiAccounts
    users_colln = accounts_service.get_users_colln(org_name)
    if projection is not None:
        if 0 in projection.values():
            projection.pop('jsonClass', None)
        else:
            projection.update({"jsonClass": 1})

    group_json = users_colln.get(group_id, projection=projection)

    return JsonObject.make_from_dict(group_json)


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
