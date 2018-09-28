import logging

from flask import request
from vedavaapi.common import VedavaapiServices


def get_user():
    from flask import session
    from sanskrit_data.schema.common import JsonObject
    return JsonObject.make_from_dict(session.get('user', None))


def check_permission(db_name="ullekhanam"):
    from flask import session
    user = get_user()
    logging.debug(request.cookies)
    logging.debug(session)
    logging.debug(session.get('user', None))
    logging.debug(user)
    if user is None or not user.check_permission(service=db_name, action="write"):
        return False
    else:
        return True


def check_and_get_repo_name():
    # check and retrieve present repo_name
    import flask
    repo_name = flask.session.get('repo_name', VedavaapiServices.lookup('store').default_repo)
    if repo_name is None:
        error = error_response(message='repo not setted', code=404)
        response = flask.make_response(
            flask.jsonify(error[0]),  # json
            error[1]  # code
        )
        flask.abort(response)
    elif repo_name not in VedavaapiServices.lookup('store').repo_names():
        error = error_response(message='invalid repo, resetting it', code=404)
        response = flask.make_response(
            flask.jsonify(error[0]),  # json
            error[1]  # code
        )
        del flask.session['repo_name']
        flask.abort(response)

    return repo_name


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

