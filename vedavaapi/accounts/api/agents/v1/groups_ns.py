from flask import g
import flask_restplus
import six
from jsonschema import ValidationError

from sanskrit_ld.helpers.permissions_helper import PermissionResolver
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.base import ObjectPermissions
from vedavaapi.objectdb import objstore_helper

from vedavaapi.common.api_common import jsonify_argument, check_argument_type, error_response, abort_with_error_response
from vedavaapi.common.token_helper import require_oauth, current_token

from . import api
from .users_ns import get_requested_agents, _validate_projection
from ....agents_helpers import groups_helper

groups_ns = api.namespace('groups', path='/groups', description='groups namespace')


@groups_ns.route('')
class Groups(flask_restplus.Resource):

    get_parser = api.parser()
    get_parser.add_argument('selector_doc', location='args', type=str, default='{}')
    get_parser.add_argument('projection', location='args', type=str)
    get_parser.add_argument('start', location='args', type=int)
    get_parser.add_argument('count', location='args', type=int)
    get_parser.add_argument('sort_doc', location='args', type=str)

    post_parser = api.parser()
    post_parser.add_argument('group_json', location='form', type=str, required=True)
    post_parser.add_argument('return_projection', location='form', type=str)

    @groups_ns.expect(get_parser, validate=True)
    @require_oauth()
    def get(self):
        args = self.get_parser.parse_args()

        group_jsons = get_requested_agents(
            args, g.users_colln,
            current_token.user_id, current_token.group_ids,  filter_doc={"jsonClass": "UsersGroup"})
        return group_jsons

    @groups_ns.expect(post_parser, validate=True)
    @require_oauth()
    def post(self):
        args = self.post_parser.parse_args()

        group_json = jsonify_argument(args['group_json'], key='group_json')
        check_argument_type(group_json, (dict,), key='group_json')

        return_projection = jsonify_argument(args.get('return_projection', None), key='return_projection')
        check_argument_type(return_projection, (dict,), key='return_projection', allow_none=True)
        _validate_projection(return_projection)
        return_projection = objstore_helper.modified_projection(
            return_projection, mandatory_attrs=['_id', 'jsonClass'])

        try:
            new_group_id = groups_helper.create_new_group(
                g.users_colln, group_json,
                current_token.user_id, current_token.group_ids, initial_agents=g.initial_agents)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValidationError as e:
            return error_response(message='invalid schema for group_json', code=403, details={"error": str(e)})

        new_group_json = g.users_colln.get(new_group_id, projection=return_projection)
        return new_group_json


@groups_ns.route('/<group_identifier>')
class GroupResource(flask_restplus.Resource):

    get_parser = groups_ns.parser()
    get_parser.add_argument('identifier_type', type=str, location='args', default='_id', choices=['_id', 'groupName'])
    get_parser.add_argument('projection', type=str, location='args')

    post_parser = groups_ns.parser()
    post_parser.add_argument('identifier_type', type=str, location='form', default='_id', choices=['_id', 'groupName'])
    post_parser.add_argument('update_doc', type=str, location='form', required=True)
    post_parser.add_argument('return_projection', type=str, location='form')

    @staticmethod
    def _group_selector_doc(group_identifier, identifier_type):
        if identifier_type not in ('_id', 'groupName'):
            error = error_response(message='invalid identifier_type', code=400)
            abort_with_error_response(error)
        return {
            "_id": groups_helper.get_group_selector_doc(_id=group_identifier),
            "userName": groups_helper.get_group_selector_doc(group_name=group_identifier)
        }.get(identifier_type)

    @groups_ns.expect(get_parser, validate=True)
    @require_oauth()
    def get(self, group_identifier):
        args = self.get_parser.parse_args()

        identifier_type = args.get('identifier_type', '_id')
        group_selector_doc = self._group_selector_doc(group_identifier, identifier_type)

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        _validate_projection(projection)
        projection = objstore_helper.modified_projection(projection, mandatory_attrs=["_id", "jsonClass"])

        group = JsonObject.make_from_dict(g.users_colln.find_one(group_selector_doc, projection=None))
        if group is None:
            return error_response(message='group not found', code=404)

        if not PermissionResolver.resolve_permission(
                group, ObjectPermissions.READ, current_token.user_id, current_token.group_ids, g.users_colln):
            return error_response(message='permission denied', code=403)

        group_json = group.to_json_map()
        projected_group_json = objstore_helper.project_doc(group_json, projection)
        return projected_group_json

    @groups_ns.expect(post_parser, validate=True)
    @require_oauth()
    def post(self, group_identifier):
        args = self.get_parser.parse_args()

        identifier_type = args.get('identifier_type', '_id')
        group_selector_doc = self._group_selector_doc(group_identifier, identifier_type)

        update_doc = jsonify_argument(args['update_doc'], key='update_doc')
        check_argument_type(update_doc, (dict,), key='update_doc')

        if 'jsonClass' not in update_doc:
            update_doc['jsonClass'] = 'UsersGroup'
        if update_doc['jsonClass'] != 'UsersGroup':
            return error_response(message='invalid jsonClass', code=403)

        if identifier_type == '_id':
            update_doc.pop('groupName', None)
            if update_doc['_id'] != group_identifier:
                return error_response(message='invalid user_id', code=403)
        else:
            group_id = groups_helper.get_group_id(g.users_colln, group_identifier)
            if not group_id:
                return error_response(message='no group with group_name {}'.format(group_identifier))
            update_doc['_id'] = group_id

        return_projection = jsonify_argument(args.get('return_projection', None), key='return_projection')
        check_argument_type(return_projection, (dict,), key='return_projection', allow_none=True)
        _validate_projection(return_projection)
        return_projection = objstore_helper.modified_projection(
            return_projection, mandatory_attrs=['_id', 'jsonClass'])

        try:
            group_update = JsonObject.make_from_dict(update_doc)
            updated_group_id = objstore_helper.update_resource(
                g.users_colln, group_update, current_token.user_id, current_token.group_ids,
                not_allowed_attributes=['members', 'groupName'])
            if updated_group_id is None:
                raise objstore_helper.ObjModelException('group not exist', 404)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValueError as e:
            return error_response(message='schema validation error', code=403, details={"error": str(e)})

        group_json = g.users_colln.find_one(group_selector_doc, projection=return_projection)
        return group_json


@groups_ns.route('/<group_identifier>/members')
class Members(flask_restplus.Resource):

    get_parser = groups_ns.parser()
    get_parser.add_argument('identifier_type', type=str, location='args', default='_id', choices=['_id', 'groupName'])

    post_parser = groups_ns.parser()
    post_parser.add_argument('identifier_type', type=str, location='form', default='_id', choices=['_id', 'groupName'])
    post_parser.add_argument('member_ids', type=str, location='form', required=True)

    delete_parser = groups_ns.parser()
    delete_parser.add_argument(
        'identifier_type', type=str, location='form', default='_id', choices=['_id', 'groupName'])
    delete_parser.add_argument('member_ids', type=str, location='form', required=True)

    @groups_ns.expect(get_parser, validate=True)
    @require_oauth()
    def get(self, group_identifier):
        args = self.get_parser.parse_args()

        identifier_type = args.get('identifier_type', '_id')
        # noinspection PyProtectedMember
        group_selector_doc = GroupResource._group_selector_doc(group_identifier, identifier_type)

        group = JsonObject.make_from_dict(g.users_colln.find_one(group_selector_doc, projection=None))
        if group is None:
            return error_response(message='group not found', code=404)

        if not PermissionResolver.resolve_permission(
                group, ObjectPermissions.READ, current_token.user_id, current_token.group_ids, g.users_colln):
            return error_response(message='permission denied', code=403)

        member_ids = group.members if hasattr(group, 'members') else []
        return member_ids

    @groups_ns.expect(post_parser, validate=True)
    @require_oauth()
    def post(self, group_identifier):
        args = self.post_parser.parse_args()

        identifier_type = args.get('identifier_type', '_id')
        # noinspection PyProtectedMember
        group_selector_doc = GroupResource._group_selector_doc(group_identifier, identifier_type)

        user_ids = jsonify_argument(args['member_ids'], key='member_ids')
        check_argument_type(user_ids, (list, ), key='member_ids')
        for user_id in user_ids:
            if not isinstance(user_id, six.string_types):
                return error_response(message='invalid user_ids', code=400)

        try:
            # noinspection PyUnusedLocal
            modified_count = groups_helper.add_users_to_group(
                g.users_colln, group_selector_doc, user_ids, current_token.user_id, current_token.group_ids)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        member_ids = g.users_colln.find_one(group_selector_doc, projection={"members": 1}).get('members', [])
        return member_ids

    @groups_ns.expect(delete_parser, validate=True)
    @require_oauth()
    def delete(self, group_identifier):
        args = self.delete_parser.parse_args()

        identifier_type = args.get('identifier_type', '_id')
        # noinspection PyProtectedMember
        group_selector_doc = GroupResource._group_selector_doc(group_identifier, identifier_type)

        user_ids = jsonify_argument(args['member_ids'], key='member_ids')
        check_argument_type(user_ids, (list,), key='member_ids')
        for user_id in user_ids:
            if not isinstance(user_id, six.string_types):
                return error_response(message='invalid user_ids', code=400)

        try:
            # noinspection PyUnusedLocal
            modified_count = groups_helper.remove_users_from_group(
                g.users_colln, group_selector_doc, user_ids, current_token.user_id, current_token.group_ids)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        member_ids = g.users_colln.find_one(group_selector_doc, projection={"members": 1}).get('members', [])
        return member_ids
