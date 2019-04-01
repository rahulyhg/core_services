import bcrypt
from flask import g
import flask_restplus

from sanskrit_ld.schema import JsonObject
from vedavaapi.objectdb.helpers import ObjModelException, projection_helper, objstore_helper

from vedavaapi.common.helpers.api_helper import error_response, jsonify_argument, check_argument_type, abort_with_error_response
from vedavaapi.common.helpers.token_helper import require_oauth, current_token

from . import api
from .users_ns import _validate_projection
from ... import sign_out_user
from ....agents_helpers import users_helper, groups_helper

me_ns = api.namespace('me', path='/me', description='personalization namespace')


def resolve_user_id():
    if current_token.user_id:
        return current_token.user_id
    elif g.current_user_id:
        return g.current_user_id
    else:
        message = "not authorized on behalf of any user" if current_token.client_id else "not authorized"
        error = error_response(message=message, code=401)
        abort_with_error_response(error)


# noinspection PyMethodMayBeStatic
@me_ns.route('')
class Me(flask_restplus.Resource):

    get_parser = me_ns.parser()
    get_parser.add_argument('projection', type=str, location='args')

    post_parser = me_ns.parser()
    post_parser.add_argument('update_doc', type=str, location='form', required=True)
    post_parser.add_argument('return_projection', type=str, location='form')

    @me_ns.expect(get_parser, validate=True)
    @require_oauth(token_required=False)
    def get(self):
        user_id = resolve_user_id()
        args = self.get_parser.parse_args()

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        _validate_projection(projection)
        projection = projection_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

        current_user_json = g.users_colln.find_one(
            users_helper.get_user_selector_doc(_id=user_id), projection=projection)
        if current_user_json is None:
            sign_out_user(g.current_org_name)
            return error_response(message='not authorized', code=401)
        return current_user_json, 200

    @me_ns.expect(post_parser, validate=True)
    @require_oauth(token_required=False)
    def post(self):
        user_id = resolve_user_id()
        group_ids = [
            group['_id'] for group in groups_helper.get_user_groups(
                g.users_colln, user_id, groups_projection={"_id": 1})
        ]

        args = self.post_parser.parse_args()
        update_doc = jsonify_argument(args['update_doc'], key='update_doc')
        check_argument_type(update_doc, (dict,), key='update_doc')
        if '_id' not in update_doc:
            update_doc['_id'] = user_id
        if 'jsonClass' not in update_doc:
            update_doc['jsonClass'] = 'User'

        if update_doc['_id'] != user_id:
            return error_response(message='invalid _id', code=403)
        if update_doc['jsonClass'] != 'User':
            return error_response(message='invalid jsonClass', code=403)

        if 'password' in update_doc:
            update_doc['hashedPassword'] = bcrypt.hashpw(
                update_doc['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            update_doc.pop('password')

        return_projection = jsonify_argument(args.get('return_projection', None), key='return_projection')
        check_argument_type(return_projection, (dict,), key='return_projection', allow_none=True)
        _validate_projection(return_projection)
        return_projection = projection_helper.modified_projection(
            return_projection, mandatory_attrs=['_id', 'jsonClass'])

        try:
            user_update = JsonObject.make_from_dict(update_doc)
            updated_user_id = objstore_helper.update_resource(
                g.users_colln, user_update.to_json_map(), user_id, group_ids,
                not_allowed_attributes=('externalAuthentications', 'password'))
            if updated_user_id is None:
                raise ObjModelException('user not exist', 404)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValueError as e:
            return error_response(message='schema validation error', code=403, details={"error": str(e)})

        user_json = g.users_colln.get(user_id, projection=return_projection)
        return user_json


@me_ns.route('/groups')
class UserGroups(flask_restplus.Resource):

    get_parser = me_ns.parser()
    get_parser.add_argument(
        'groups_projection', type=str, location='args', default=None, help='projection for each group'
    )

    @me_ns.expect(get_parser, validate=True)
    @require_oauth(token_required=False)
    def get(self):
        user_id = resolve_user_id()

        args = self.get_parser.parse_args()

        groups_projection = jsonify_argument(args.get('groups_projection', None), key='groups_projection')
        check_argument_type(groups_projection, (dict, ), allow_none=True)
        _validate_projection(groups_projection)

        user_group_jsons = groups_helper.get_user_groups(g.users_colln, user_id, groups_projection=None)

        for group_json in user_group_jsons:
            projection_helper.project_doc(group_json, groups_projection, in_place=True)

        return user_group_jsons, 200
