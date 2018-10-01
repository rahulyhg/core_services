import flask_restplus
from flask import Blueprint

from .. import myservice


api_blueprint_v1 = Blueprint(myservice().name+'_v1', __name__)


api = flask_restplus.Api(
    app=api_blueprint_v1,
    version='1.0',
    prefix='/v1',
    title=myservice().title,
    description="an api endpoint to configure repos.",
    doc='/v1'
)


from . import rest
