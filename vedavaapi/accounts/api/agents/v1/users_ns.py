from collections import OrderedDict

from flask import g
import flask_restplus
from jsonschema import ValidationError

from sanskrit_ld.helpers.permissions_helper import PermissionResolver
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.base import ObjectPermissions
from vedavaapi.accounts.agents_helpers import groups_helper
from vedavaapi.objectdb.helpers import ObjModelException, projection_helper, objstore_helper

from vedavaapi.common.api_common import jsonify_argument, check_argument_type, error_response, abort_with_error_response
from vedavaapi.common.token_helper import require_oauth, current_token

from . import api
from ....agents_helpers import users_helper

users_ns = api.namespace('users', path='/users', description='users namespace')


def _validate_projection(projection):
    try:
        projection_helper.validate_projection(projection)
    except ObjModelException as e:
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
    projection = projection_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

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

    delete_parser = api.parser()
    delete_parser.add_argument('user_ids', location='form', type=str, required=True)

    @users_ns.expect(get_parser, validate=True)
    @require_oauth()
    def get(self):
        args = self.get_parser.parse_args()

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        _validate_projection(projection)
        projection = projection_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

        args_copy = args.copy()
        args_copy.pop('projection', None)
        user_jsons = get_requested_agents(
            args_copy, g.users_colln, current_token.user_id, current_token.group_ids, filter_doc={"jsonClass": "User"})

        projected_user_jsons = [users_helper.project_user_json(uj, projection=projection) for uj in user_jsons]
        return projected_user_jsons

    @users_ns.expect(post_parser, validate=True)
    def post(self):
        args = self.post_parser.parse_args()

        if g.current_user_id:
            return error_response(message='you are already registered', code=403)

        user_json = jsonify_argument(args['user_json'], key='user_json')  # type: dict
        check_argument_type(user_json, (dict, ), key='user_json')

        return_projection = jsonify_argument(args.get('return_projection', None), key='return_projection')
        check_argument_type(return_projection, (dict, ), key='return_projection', allow_none=True)
        _validate_projection(return_projection)
        return_projection = projection_helper.modified_projection(
            return_projection, mandatory_attrs=['_id', 'jsonClass'])

        try:
            new_user_id = users_helper.create_new_user(g.users_colln, user_json, initial_agents=g.initial_agents)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValidationError as e:
            return error_response(message='invalid schema for user_json', code=403, details={"error": str(e)})

        new_user_json = g.users_colln.get(new_user_id, projection=return_projection)
        return new_user_json

    @users_ns.expect(delete_parser, validate=True)
    @require_oauth()
    def delete(self):
        args = self.delete_parser.parse_args()

        user_ids = jsonify_argument(args['user_ids'])
        check_argument_type(user_ids, (list,))

        ids_validity = False not in [isinstance(_id, str) for _id in user_ids]
        if not ids_validity:
            return error_response(message='ids should be strings', code=404)

        delete_report = []

        for user_id in user_ids:
            deleted, deleted_res_ids = objstore_helper.delete_tree(
                g.users_colln, user_id, current_token.user_id, current_token.group_ids)

            delete_report.append({
                "deleted": deleted,
                "deleted_resource_ids": deleted_res_ids
            })

        return delete_report


@users_ns.route('/<user_id>')
class UserResource(flask_restplus.Resource):

    get_parser = users_ns.parser()
    get_parser.add_argument('projection', type=str, location='args')

    post_parser = users_ns.parser()
    post_parser.add_argument('update_doc', type=str, location='form', required=True)
    post_parser.add_argument('return_projection', type=str, location='form')

    @users_ns.expect(get_parser, validate=True)
    @require_oauth()
    def get(self, user_id):
        args = self.get_parser.parse_args()
        user_selector_doc = users_helper.get_user_selector_doc(_id=user_id)

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        _validate_projection(projection)
        projection = projection_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

        user = JsonObject.make_from_dict(g.users_colln.find_one(user_selector_doc, projection=None))
        if user is None:
            return error_response(message='user not found', code=404)

        if not PermissionResolver.resolve_permission(
                user, ObjectPermissions.READ, current_token.user_id, current_token.group_ids, g.users_colln):
            return error_response(message='permission denied', code=403)

        user_json = user.to_json_map()
        projected_user_json = users_helper.project_user_json(user_json, projection=projection)
        return projected_user_json

    @users_ns.expect(post_parser, validate=True)
    @require_oauth()
    def post(self, user_id):
        '''
        if not current_token.user_id:
            return error_response(message='not authorized', code=401)
        '''
        args = self.post_parser.parse_args()
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
        return_projection = projection_helper.modified_projection(
            return_projection, mandatory_attrs=['_id', 'jsonClass'])

        try:
            user_update = JsonObject.make_from_dict(update_doc)
            updated_user_id = objstore_helper.update_resource(
                g.users_colln, user_update.to_json_map(), current_token.user_id, current_token.group_ids,
                not_allowed_attributes=['hashedPassword', 'externalAuthentications', 'password'])
            if updated_user_id is None:
                raise ObjModelException('user not exist', 404)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except (ValueError, ValidationError, TypeError) as e:
            return error_response(message='schema validation error', code=403, details={"error": str(e)})

        user_json = g.users_colln.find_one(user_selector_doc, projection=return_projection)
        return user_json


@users_ns.route('/<user_id>/groups')
class UserGroups(flask_restplus.Resource):

    get_parser = users_ns.parser()
    get_parser.add_argument('groups_projection', type=str, location='args', default=None, help='projection for each group')

    @users_ns.expect(get_parser, validate=True)
    @require_oauth()
    def get(self, user_id):
        '''
        if not current_token.user_id:
            return error_response()
        '''
        args = self.get_parser.parse_args()
        user_selector_doc = users_helper.get_user_selector_doc(_id=user_id)

        groups_projection = jsonify_argument(args.get('groups_projection', None), key='groups_projection')
        check_argument_type(groups_projection, (dict, ), allow_none=True)
        _validate_projection(groups_projection)

        user_json = g.users_colln.find_one(user_selector_doc, projection={"_id": 1, "permissions": 1})
        if not user_json:
            return error_response(message='user not found', code=404)

        if not PermissionResolver.resolve_permission(
                user_json, ObjectPermissions.READ, current_token.user_id, current_token.group_ids, g.users_colln):
            return error_response(message='permission denied', code=403)

        user_group_jsons = groups_helper.get_user_groups(g.users_colln, user_id, groups_projection=None)
        permitted_user_group_jsons = []

        for group_json in user_group_jsons:
            if PermissionResolver.resolve_permission(
                group_json, ObjectPermissions.READ, current_token.user_id, current_token.group_ids, g.users_colln):

                projection_helper.project_doc(group_json, groups_projection, in_place=True)
                permitted_user_group_jsons.append(group_json)

        return permitted_user_group_jsons, 200

