from collections import OrderedDict

import flask_restplus
from jsonschema import ValidationError
from sanskrit_ld.helpers.permissions_helper import PermissionResolver

from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.base import ObjectPermissions

from vedavaapi.common.api_common import jsonify_argument, check_argument_type, error_response, abort_with_error_response
from vedavaapi.common.api_common import get_current_user_id, get_current_user_group_ids
from vedavaapi.objectdb import objstore_helper

from ....agents_helpers import users_helper
from . import api
from ... import get_users_colln, get_initial_agents


users_ns = api.namespace('users', path='/users', description='users namespace')


def _validate_projection(projection):
    try:
        objstore_helper.validate_projection(projection)
    except objstore_helper.ObjModelException as e:
        error = error_response(message=e.message, code=e.http_response_code)
        abort_with_error_response(error)


def get_requested_agents(args, colln, user_id, group_ids, filter_doc=None):
    selector_doc = jsonify_argument(args.get('selector_doc', None), key='selector_doc') or {}
    check_argument_type(selector_doc, (dict,), key='selector_doc')
    if filter_doc is not None:
        selector_doc.update(filter_doc)

    projection = jsonify_argument(args.get('projection', None), key='projection')
    check_argument_type(projection, (dict,), key='projection', allow_none=True)
    _validate_projection(projection)
    projection = objstore_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

    lrs_request_doc = jsonify_argument(args.get('linked_resources', None), 'linked_resources')
    check_argument_type(lrs_request_doc, (dict,), key='linked_resources', allow_none=True)

    sort_doc = jsonify_argument(args.get('sort_doc', None), key='sort_doc')
    check_argument_type(sort_doc, (dict, list), key='sort_doc', allow_none=True)

    ops = OrderedDict()
    if sort_doc is not None:
        ops['sort'] = [sort_doc]
    if args.get('start', None) is not None and args.get('count', None) is not None:
        ops['skip'] = [args['start']]
        ops['limit'] = [args['count']]

    try:
        resource_repr_jsons = objstore_helper.get_read_permitted_resource_jsons(
            colln, user_id, group_ids, selector_doc, projection=projection, ops=ops)
    except (TypeError, ValueError):
        error = error_response(message='arguments to operations seems invalid', code=400)
        abort_with_error_response(error)

    if lrs_request_doc is not None:
        # noinspection PyUnboundLocalVariable
        for rj in resource_repr_jsons:
            linked_resources = objstore_helper.get_linked_resource_ids(colln, rj['_id'], lrs_request_doc)
            rj['linked_resources'] = linked_resources
    return resource_repr_jsons


@users_ns.route('')
class Users(flask_restplus.Resource):

    get_parser = api.parser()
    get_parser.add_argument('selector_doc', location='args', type=str, default='{}')
    get_parser.add_argument('projection', location='args', type=str)
    get_parser.add_argument('start', location='args', type=int)
    get_parser.add_argument('count', location='args', type=int)
    get_parser.add_argument('sort_doc', location='args', type=str)

    post_parser = api.parser()
    post_parser.add_argument('user_json', location='form', type=str, required=True)
    post_parser.add_argument('return_projection', location='form', type=str)

    @users_ns.expect(get_parser, validate=True)
    def get(self):
        args = self.get_parser.parse_args()
        users_colln = get_users_colln()
        current_user_id = get_current_user_id(required=True)
        current_user_group_ids = get_current_user_group_ids()

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        _validate_projection(projection)
        projection = objstore_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

        args_copy = args.copy()
        args_copy.pop('projection', None)
        user_jsons = get_requested_agents(
            args_copy, users_colln, current_user_id, current_user_group_ids, filter_doc={"jsonClass": "User"})

        projected_user_jsons = [users_helper.project_user_json(uj, projection=projection) for uj in user_jsons]
        return projected_user_jsons

    @users_ns.expect(post_parser, validate=True)
    def post(self):
        args = self.post_parser.parse_args()
        users_colln = get_users_colln()
        current_user_id = get_current_user_id()

        if current_user_id:
            return error_response(message='you are already registered', code=403)

        user_json = jsonify_argument(args['user_json'], key='user_json')  # type: dict
        check_argument_type(user_json, (dict, ), key='user_json')

        return_projection = jsonify_argument(args.get('return_projection', None), key='return_projection')
        check_argument_type(return_projection, (dict, ), key='return_projection', allow_none=True)
        _validate_projection(return_projection)
        return_projection = objstore_helper.modified_projection(
            return_projection, mandatory_attrs=['_id', 'jsonClass'])

        try:
            new_user_id = users_helper.create_new_user(users_colln, user_json, initial_agents=get_initial_agents())
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValidationError as e:
            return error_response(message='invalid schema for user_json', code=403, details={"error": str(e)})

        new_user_json = users_colln.get(new_user_id, projection=return_projection)
        return new_user_json


@users_ns.route('/<user_id>')
class UserResource(flask_restplus.Resource):

    get_parser = users_ns.parser()
    get_parser.add_argument('projection', type=str, location='args')

    post_parser = users_ns.parser()
    post_parser.add_argument('update_doc', type=str, location='form', required=True)
    post_parser.add_argument('return_projection', type=str, location='form')

    @users_ns.expect(get_parser, validate=True)
    def get(self, user_id):
        current_user_id = get_current_user_id(required=True)
        current_user_group_ids = get_current_user_group_ids()
        args = self.get_parser.parse_args()
        users_colln = get_users_colln()
        user_selector_doc = users_helper.get_user_selector_doc(_id=user_id)

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        _validate_projection(projection)
        projection = objstore_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

        user = JsonObject.make_from_dict(users_colln.find_one(user_selector_doc, projection=None))
        if user is None:
            return error_response(message='user not found', code=404)

        if not PermissionResolver.resolve_permission(
                user, ObjectPermissions.READ, current_user_id, current_user_group_ids, users_colln):
            return error_response(message='permission denied', code=403)

        user_json = user.to_json_map()
        projected_user_json = users_helper.project_user_json(user_json, projection=projection)
        return projected_user_json

    @users_ns.expect(post_parser, validate=True)
    def post(self, user_id):
        args = self.post_parser.parse_args()
        users_colln = get_users_colln()
        current_user_id = get_current_user_id(required=True)
        current_user_group_ids = get_current_user_group_ids()

        user_selector_doc = users_helper.get_user_selector_doc(_id=user_id)

        update_doc = jsonify_argument(args['update_doc'], key='update_doc')
        check_argument_type(update_doc, (dict,), key='update_doc')
        if '_id' not in update_doc:
            update_doc['_id'] = user_id
        if 'jsonClass' not in update_doc:
            update_doc['jsonClass'] = 'User'

        if update_doc['_id'] != user_id:
            return error_response(message='invalid user_id', code=403)
        if update_doc['jsonClass'] != 'User':
            return error_response(message='invalid jsonClass', code=403)

        return_projection = jsonify_argument(args.get('return_projection', None), key='return_projection')
        check_argument_type(return_projection, (dict,), key='return_projection', allow_none=True)
        _validate_projection(return_projection)
        return_projection = objstore_helper.modified_projection(
            return_projection, mandatory_attrs=['_id', 'jsonClass'])

        try:
            user_update = JsonObject.make_from_dict(update_doc)
            updated_user_id = objstore_helper.update_resource(
                users_colln, user_update, current_user_id, current_user_group_ids,
                not_allowed_attributes=['hashedPassword', 'externalAuthentications', 'password'])
            if updated_user_id is None:
                raise objstore_helper.ObjModelException('user not exist', 404)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValueError as e:
            return error_response(message='schema validation error', code=403, details={"error": str(e)})

        user_json = users_colln.find_one(user_selector_doc, projection=return_projection)
        return user_json
