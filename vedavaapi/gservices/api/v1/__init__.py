import json, os.path

from flask import Blueprint
from flask_restplus import Api
from .. import gservices

def creds_dict():
    #lazy loading credentials after servivce object initialization.
    credentials_dict = json.load(open(os.path.join(gservices.ServiceObj.config['google_creds_base_dir'], gservices.ServiceObj.config['credentials_path'])))
    return credentials_dict

v1_bp = Blueprint('gproxy_api_v1', __name__)

v1_api = Api(app=v1_bp, version='1.0', title='gproxy_api-v1', description='gproxy api. a proxy for google apis with pre determined credentials.')
from .gdrive import gdrive_ns
from .gsheets import gsheets_ns

v1_api.add_namespace(gdrive_ns, path='/gdrive')
v1_api.add_namespace(gsheets_ns, path='/gsheets')
