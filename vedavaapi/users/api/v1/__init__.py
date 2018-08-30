import logging, os.path

import flask_restplus, flask

URL_PREFIX = '/v1'
api_blueprint = flask.Blueprint(name='auth1', import_name=__name__)

api = flask_restplus.Api(app=api_blueprint, version='1.0', prefix=URL_PREFIX, title="Users")
from . import rest
