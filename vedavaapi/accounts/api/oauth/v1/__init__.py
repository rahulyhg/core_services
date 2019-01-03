import flask_restplus
from flask import Blueprint


api_blueprint_v1 = Blueprint('oauth_server'+'_v1', __name__, static_folder='static', static_url_path='/static')


api = flask_restplus.Api(
    app=api_blueprint_v1,
    version='1.0',
    title='Vedavaapi OAuth Server',
    description='Vedavaapi OAuth Server Api',
    doc='/docs')


from . import authorization_ns
from . import clients_ns
