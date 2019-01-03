import flask_restplus
from flask import session
from jsonschema import ValidationError
from sanskrit_ld.schema.oauth import OAuth2Client
from vedavaapi.common.api_common import error_response, jsonify_argument, check_argument_type
from werkzeug.security import gen_salt

from . import api
from ... import get_users_colln, get_oauth_colln, get_current_user_id
from ....agents_helpers.models import User
from ....oauth_server_helpers.models import OAuth2Client


clients_ns = api.namespace('clients', path='/clients')


def get_current_user():
    user_id = get_current_user_id()
    if not user_id:
        return None
    users_colln = get_users_colln()
    user = User.get_user(users_colln, _id=user_id)
    return user


@clients_ns.route('')
class Clients(flask_restplus.Resource):

    get_parser = clients_ns.parser()
    get_parser.add_argument('projection', type=str, location='args')

    @clients_ns.expect(get_parser, validate=True)
    def get(self):
        oauth_colln = get_oauth_colln()
        users_colln = get_users_colln()
        args = self.get_parser.parse_args()
        current_user_id = get_current_user_id()

        if current_user_id is None:
            return error_response(message='not authorized', code=401)

        current_user = User.get_user(users_colln, _id=current_user_id)
        if current_user is None:
            session.pop('user_id', None)
            return error_response(message='not authorized', code=401)

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        if projection and 0 in projection.values() and 1 in projection.values():
            return error_response(message='invalid projection', code=400)

        clients_selector_doc = {
            "jsonClass": "OAuth2Client",
            "user_id": current_user_id
        }
        return list(oauth_colln.find(clients_selector_doc, projection=projection)), 200

