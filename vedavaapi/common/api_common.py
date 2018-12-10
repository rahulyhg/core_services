import json
import logging

from flask import request
import flask
from vedavaapi.common import VedavaapiServices


def get_user(required=False):
    from flask import session
    from sanskrit_ld.schema import JsonObject
    user = JsonObject.make_from_dict(session.get('user', None))
    if user is None and required:
        message = 'you must login to perform requested action'
        error = error_response(message=message, code=401)
        abort_with_error_response(error)
    return user


def get_repo():
    # check and retrieve present repo_name
    repo_name = flask.session.get('repo_name', VedavaapiServices.lookup('store').default_repo)
    check_repo(repo_name)
    return repo_name


def check_permission(svc_name):
    from flask import session
    user = get_user()
    logging.debug(request.cookies)
    logging.debug(session)
    logging.debug(session.get('user', None))
    logging.debug(user)
    if user is None or not user.check_permission(service=svc_name, action="write"):
        return False
    else:
        return True


def check_repo(repo_name):
    if repo_name is None:
        error = error_response(message='repo not setted', code=403)
        abort_with_error_response(error)
    elif repo_name not in VedavaapiServices.lookup('store').repo_names():
        del flask.session['repo_name']
        error = error_response(message='invalid repo, resetting it', code=403)
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


def abort_with_error_response(error):
    response = flask.make_response(
        flask.jsonify(error[0]),  # json
        error[1]  # code
    )
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
    return {'jsonClass': 'Error', 'error': error}, error['code']
