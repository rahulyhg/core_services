import json
from flask import Blueprint
from flask_restplus import Api

from vedavaapi.common.api_common import check_and_get_repo_name

from ... import myservice


def creds_dict():
    credentials_dict = json.load(open(myservice().creds_path(check_and_get_repo_name())))
    return credentials_dict


v1_bp = Blueprint('gproxy_api_v1', __name__)

api = Api(app=v1_bp, version='1.0', title='gproxy',
          description='gproxy api. a proxy for google apis with pre determined credentials.')

from .gdrive import gdrive_ns
from .gsheets import gsheets_ns

api.add_namespace(gdrive_ns, path='/gdrive')
api.add_namespace(gsheets_ns, path='/gsheets')
