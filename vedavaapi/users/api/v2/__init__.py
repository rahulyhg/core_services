import logging, os.path

import flask_restplus, flask


URL_PREFIX = '/v2'
api_blueprint = flask.Blueprint(name='auth2', import_name=__name__)

api = flask_restplus.Api(app=api_blueprint, version='2.0', prefix=URL_PREFIX)

from ..v2 import rest
