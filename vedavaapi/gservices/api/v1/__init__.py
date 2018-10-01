from flask import Blueprint
from flask_restplus import Api

from .. import myservice


api_blueprint_v1 = Blueprint(myservice().name+'_v1', __name__)

api = Api(
    app=api_blueprint_v1,
    version='1.0',
    title=myservice().title,
    prefix='/v1',
    description=myservice().description,
    doc='/v1'
)


from .gdrive import gdrive_ns
from .gsheets import gsheets_ns


api.add_namespace(gdrive_ns, path='/gdrive')
api.add_namespace(gsheets_ns, path='/gsheets')
