
import flask_restplus
from flask import session
from jsonschema import ValidationError
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.base import ObjectPermissions
from sanskrit_ld.schema.users import User as _User
from vedavaapi.common.api_common import error_response, jsonify_argument, check_argument_type, \
    abort_with_error_response, get_current_user_id
from sanskrit_ld.helpers.permissions_helper import PermissionResolver
from sanskrit_ld.helpers import permissions_helper

from . import api
from ... import get_users_colln, get_initial_agents
from ....agents_helpers.models import User


users_ns = api.namespace('users', path='/users', description='users namespace')


def check_required_attrs(obj, attrs):
    for attr in attrs:
        if not hasattr(obj, attr):
            error = error_response(message='obj has no required params', code=403)
            abort_with_error_response(error)
    return


def delete_attrs(obj, attrs):
    for attr in attrs:
        if hasattr(obj, attr):
            delattr(obj, attr)


@users_ns.route('')
class Users(flask_restplus.Resource):

    post_parser = users_ns.parser()
    post_parser.add_argument('user_doc', type=str, location='form', required=True)

    @users_ns.expect(post_parser, validate=True)
    def post(self):
        # now oauth check, as user doesn't exist now
        users_colln = get_users_colln()
        args = self.post_parser.parse_args()

        user_doc = jsonify_argument(args['user_doc'], key='user_doc')
        check_argument_type(user_doc, (dict,), key='user_doc')

        new_user = JsonObject.make_from_dict(user_doc)
        check_required_attrs(new_user, ['email', 'password'])

        if User.user_exists(users_colln, email=new_user.email):
            return error_response(message='user already exists', code=403)

        session.pop('authentications', None)
        new_user_id = User.create_new_user(users_colln, new_user)

        User.add_group(
            users_colln, User.get_user_selector_doc(_id=new_user_id), get_initial_agents().all_users_group_id)

        permissions_helper.add_to_granted_list(
            users_colln, [new_user_id], ObjectPermissions.ACTIONS,
            group_pids=[get_initial_agents().root_admins_group_id])

        permissions_helper.add_to_granted_list(
            users_colln, [new_user_id],
            [ObjectPermissions.READ, ObjectPermissions.UPDATE_CONTENT, ObjectPermissions.DELETE],
            user_pids=[new_user_id]
        )

        return User.get_user_json(
            users_colln, _id=new_user_id, projection={"permissions": 0, "hashedPassword": 0}), 200


# noinspection PyMethodMayBeStatic
@users_ns.route('/<user_id>')
class UserResource(flask_restplus.Resource):

    get_parser = users_ns.parser()
    get_parser.add_argument('projection', type=str, location='args')

    post_parser = users_ns.parser()
    post_parser.add_argument('update_doc', type=str, location='form', required=True)

    @users_ns.expect(get_parser, validate=True)
    def get(self, user_id):
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()

        args = self.get_parser.parse_args()
        current_user = User.get_user(users_colln, _id=current_user_id, projection={"target": 1, "_id": 1})
        if current_user is None:
            return error_response(message='not authorized', code=401)

        user_resource_permissions_projection = User.get_user(
            users_colln, _id=user_id, projection={"permissions": 1, "target": 1, "_id": 1})
        if user_resource_permissions_projection is None:
            return error_response(message='user resource not found', code=404)

        if not PermissionResolver.resolve_permission(
                user_resource_permissions_projection,
                ObjectPermissions.READ, current_user, users_colln):
            return error_response(message='permission denied', code=403)

        projection = jsonify_argument(args.get('projection', None), key='projection')
        check_argument_type(projection, [dict], key='projection', allow_none=True)
        if projection and 0 in projection.values() and 1 in projection.values():
            return error_response(message='invalid projection', code=400)
        return User.get_user_json(users_colln, _id=user_id, projection=projection), 200

    @users_ns.expect(post_parser, validate=True)
    def post(self, user_id):
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()
        args = self.post_parser.parse_args()

        current_user = User.get_user(users_colln, _id=current_user_id, projection={"target": 1, "_id": 1})
        if current_user is None:
            return error_response(message='not authorized', code=401)

        update_doc = jsonify_argument(args['update_doc'], key='update_doc')
        check_argument_type(update_doc, (dict,), key='update_doc')

        user_resource_permissions_projection = User.get_user(
            users_colln, _id=user_id, projection={"permissions": 1, "target": 1, "_id": 1})
        if user_resource_permissions_projection is None:
            return error_response(message='user resource not found', code=404)

        if not PermissionResolver.resolve_permission(
                user_resource_permissions_projection,
                ObjectPermissions.UPDATE_CONTENT, current_user, users_colln):
            return error_response(message='permission denied', code=403)

        diff = JsonObject.make_from_dict(update_doc)
        check_argument_type(diff, (_User,), key='update_doc')
        delete_attrs(diff, ['_id', 'creator', 'created', 'permissions', 'hashedPassword', 'email'])
        User.swizzle(diff)

        try:
            diff.validate_schema(diff=True)
        except ValidationError:
            return error_response(message='arguments are invalid', code=400)

        modified = User.update_details(users_colln, User.get_user_selector_doc(_id=user_id), diff.to_json_map())

        if modified:
            user = User.get_user(users_colln, _id=user_id, projection=self.presentation_projection)
            return user.to_json_map(), 200
        else:
            return error_response(message='error in updating user info', code=400)
