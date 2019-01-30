import flask_restplus
from flask import Blueprint

from .. import myservice


api_blueprint_v1 = Blueprint('authorizer'+'_v1', __name__)


api = flask_restplus.Api(
    app=api_blueprint_v1,
    version='1.0',
    title=myservice().title,
    description=myservice().description,
    doc='/docs')


from . import auth_ns