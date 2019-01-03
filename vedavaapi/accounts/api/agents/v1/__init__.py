import flask_restplus
from flask import Blueprint

from vedavaapi.accounts.api import myservice


api_blueprint_v1 = Blueprint('agents'+'_v1', __name__)


api = flask_restplus.Api(
    app=api_blueprint_v1,
    version='1.0',
    title='Vedavaapi Agents Manager',
    description='Vedavaapi Agents Manager Api',
    doc='/docs')


from . import default_ns
from . import me_ns
from . import users_ns
from . import groups_ns
