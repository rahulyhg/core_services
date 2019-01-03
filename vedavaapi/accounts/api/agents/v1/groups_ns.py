import sys

import flask_restplus
from jsonschema import ValidationError
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.base import ObjectPermissions
from vedavaapi.common.api_common import error_response, jsonify_argument, check_argument_type, abort_with_error_response, get_current_user_id
from sanskrit_ld.helpers.permissions_helper import PermissionResolver
from sanskrit_ld.schema.users import UsersGroup as _UserGroup
from sanskrit_ld.helpers import permissions_helper

from . import api
from ... import get_users_colln, get_initial_agents
from ....agents_helpers.models import User, UserGroup


groups_ns = api.namespace('groups', path='/groups', description='groups namespace')

def delete_attrs(obj, attrs):
    for attr in attrs:
        if hasattr(obj, attr):
            delattr(obj, attr)


def check_required_attrs(obj, attrs):
    for attr in attrs:
        if not hasattr(obj, attr):
            error = error_response(message='obj has no required params', code=403)
            abort_with_error_response(error)
    return


@groups_ns.route('')
class Groups(flask_restplus.Resource):

    post_parser = groups_ns.parser()
    post_parser.add_argument('group_doc', type=str, location='form', required=True)

    @groups_ns.expect(post_parser, validate=True)
    def post(self):
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()
        args = self.post_parser.parse_args()

        groups_doc = jsonify_argument(args['group_doc'], key='group_doc')
        check_argument_type(groups_doc, (dict,), key='group_doc')
        group = JsonObject.make_from_dict(groups_doc)
        check_argument_type(group, (_UserGroup,), key='group_doc')
        check_required_attrs(group, ['source', 'group_name', 'name'])

        current_user = User.get_user(users_colln, _id=current_user_id, projection={"target": 1, "_id": 1})

        parent_group = UserGroup.get_group(users_colln, _id=group.source)
        if not parent_group:
            return error_response(message='parent group doesn\'t exists', code=403)

        if not PermissionResolver.resolve_permission(
                parent_group, ObjectPermissions.LINK_FROM_OTHERS, current_user, users_colln):
            return error_response(message='permission denied', code=403)

        if UserGroup.group_exists(users_colln, group_name=group.group_name):
            return error_response(message='group already exists', code=403)

        new_group_id = UserGroup.create_new_group(
            users_colln, args['group_name'], current_user_id)
        permissions_helper.add_to_granted_list(
            users_colln,
            [new_group_id],
            ObjectPermissions.ACTIONS,
            user_pids=[current_user_id],
            group_pids=[get_initial_agents().root_admins_group_id]
        )
        permissions_helper.add_to_granted_list(
            users_colln, [new_group_id], [ObjectPermissions.LIST, ObjectPermissions.READ], group_pids=[new_group_id])

        User.add_group(users_colln, current_user_id, new_group_id)

        return UserGroup.get_group_json(users_colln, _id=new_group_id), 200


@groups_ns.route('/<group_id>')
class Group(flask_restplus.Resource):

    get_parser = groups_ns.parser()
    get_parser.add_argument('projection', type=str, location='args')

    post_parser = groups_ns.parser()
    post_parser.add_argument('update_doc', type=str, location='form', required=True)

    @groups_ns.expect(get_parser, validate=True)
    def get(self, group_id):
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()

        args = self.get_parser.parse_args()
        current_user = User.get_user(users_colln, _id=current_user_id, projection={"target": 1, "_id": 1})

        group_permissions_projection = UserGroup.get_group(
            users_colln, _id=group_id, projection={"permissions": 1, "source": 1, "_id": 1})
        if group_permissions_projection is None:
            return error_response(message='group doesn\'t exist', code=404)

        if not PermissionResolver.resolve_permission(
                group_permissions_projection, ObjectPermissions.READ, current_user, users_colln):
            return error_response(message='permission denied', code=403)

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, [dict], key='projection', allow_none=True)
        if projection and 0 in projection.values() and 1 in projection.values():
            return error_response(message='invalid projection', code=400)

        return UserGroup.get_group_json(users_colln, _id=group_id, projection=projection), 200

    @groups_ns.expect(post_parser, validate=True)
    def post(self, group_id):
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()
        args = self.post_parser.parse_args()

        current_user = User.get_user(users_colln, _id=current_user_id, projection={"target": 1, "_id": 1})
        if current_user is None:
            return error_response(message='not authorized', code=401)

        update_doc = jsonify_argument(args['update_doc'], key='update_doc')
        check_argument_type(update_doc, (dict,), key='update_doc')

        group_resource_permissions_projection = UserGroup.get_group(
            users_colln, _id=group_id, projection={"permissions": 1, "target": 1, "_id": 1})
        if group_resource_permissions_projection is None:
            return error_response(message='group resource not found', code=404)

        if not PermissionResolver.resolve_permission(
                group_resource_permissions_projection,
                ObjectPermissions.UPDATE_CONTENT, current_user, users_colln):
            return error_response(message='permission denied', code=403)

        diff = JsonObject.make_from_dict(update_doc)
        check_argument_type(diff, (_UserGroup,), key='update_doc')
        delete_attrs(diff, ['_id', 'creator', 'created', 'permissions', 'groupName'])

        try:
            diff.validate_schema(diff=True)
        except ValidationError:
            return error_response(message='arguments are invalid', code=400)

        modified = UserGroup.update_details(users_colln, UserGroup.get_group_selector_doc(_id=group_id), diff.to_json_map())

        if modified:
            return UserGroup.get_group_json(users_colln, _id=group_id, projection={"permissions": 0})
        else:
            return error_response(message='error in updating user info', code=400)
