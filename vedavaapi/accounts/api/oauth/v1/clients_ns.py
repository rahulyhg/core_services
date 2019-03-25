import flask_restplus
from flask import g, request
from jsonschema import ValidationError

from vedavaapi.accounts.agents_helpers import groups_helper
from vedavaapi.common.api_common import error_response, jsonify_argument, check_argument_type
from vedavaapi.objectdb.helpers import ObjModelException, projection_helper

from . import api
from ....oauth_server_helpers import clients_helper

clients_ns = api.namespace('clients', path='/clients')


def marshal_to_google_structure(client_json):
    authorization_uri = request.url_root + 'accounts/oauth/v1/authorize'
    token_uri = request.url_root + 'accounts/oauth/v1/token'
    installed = {
        "client_id": client_json['client_id'],
        "client_secret": client_json.get('client_secret'),
        "redirect_uris": client_json.get('redirect_uris', []),
        "auth_uri": authorization_uri,
        "token_uri": token_uri
    }
    return {"installed": installed}


@clients_ns.route('')
class Clients(flask_restplus.Resource):

    get_parser = clients_ns.parser()
    get_parser.add_argument('projection', type=str, location='args')
    get_parser.add_argument(
        'marshal_to_google_structure', type=str, location='args', default='false', choices=['true', 'false']
    )

    post_parser = clients_ns.parser()
    post_parser.add_argument('client_json', type=str, location='form', required=True)
    post_parser.add_argument('client_type', type=str, location='form', required=True, choices=['public', 'private'])
    post_parser.add_argument(
        'marshal_to_google_structure', type=str, location='form', default='false', choices=['true', 'false']
    )

    @clients_ns.expect(get_parser, validate=True)
    def get(self):
        if g.current_user_id is None:
            return error_response(message='not authorized', code=401)

        args = self.get_parser.parse_args()
        projection = jsonify_argument(args.get('projection', None), key='projection')
        try:
            projection_helper.validate_projection(projection)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        clients_selector_doc = {
            "jsonClass": "OAuth2Client",
            "user_id": g.current_user_id
        }
        client_jsons = (g.oauth_colln.find(clients_selector_doc, projection=projection))
        print(args['marshal_to_google_structure'])
        if not jsonify_argument(args['marshal_to_google_structure']):
            return client_jsons
        return [marshal_to_google_structure(cj) for cj in client_jsons]

    @clients_ns.expect(post_parser, validate=True)
    def post(self):
        if g.current_user_id is None:
            return error_response(message='not authorized', code=401)
        current_user_group_ids = [
            group['_id'] for group in groups_helper.get_user_groups(
                g.users_colln, g.current_user_id, groups_projection={"_id": 1})
        ]

        args = self.post_parser.parse_args()

        client_json = jsonify_argument(args['client_json'], key='client_json')
        check_argument_type(client_json, (dict, ), key='client_json')

        client_type = args['client_type']

        try:
            new_client_id = clients_helper.create_new_client(
                g.oauth_colln, client_json, client_type, g.current_user_id, current_user_group_ids, initial_agents=None)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValidationError as e:
            return error_response(message='invalid schema for client_json', code=403, details={"error": str(e)})

        new_client_json = g.oauth_colln.find_one({"_id": new_client_id})
        if not jsonify_argument(args['marshal_to_google_structure']):
            return new_client_json
        return marshal_to_google_structure(new_client_json)
