from flask import g
import flask_restplus
from sanskrit_ld.helpers.permissions_helper import PermissionResolver

from sanskrit_ld.schema.base import Permission, ObjectPermissions
from vedavaapi.objectdb.helpers import ObjModelException, objstore_helper

from vedavaapi.common.helpers.api_helper import error_response, jsonify_argument, check_argument_type
from vedavaapi.common.helpers.token_helper import require_oauth, current_token

from . import api
from ....agents_helpers import users_helper, groups_helper

agents_ns = api.namespace('default', path='/', description='agents namespace')


# noinspection PyMethodMayBeStatic
@agents_ns.route('/initial_agents')
class InitialAgents(flask_restplus.Resource):

    def get(self):
        return {
            "root_admin_id": g.initial_agents.root_admin_id,
            "root_admins_group_id": g.initial_agents.root_admins_group_id,
            "all_users_group_id": g.initial_agents.all_users_group_id
        }


@api.route('/agents/<string:agent_id>/agents')
class ActorAgents(flask_restplus.Resource):

    post_parser = api.parser()
    post_parser.add_argument(
        'actions', location='form', type=str, required=True,
        help='any combination among {}'.format(str(ObjectPermissions.ACTIONS))
    )
    post_parser.add_argument(
        'agents_set_name', location='form', type=str, required=True, choices=[Permission.GRANTED, Permission.WITHDRAWN])
    post_parser.add_argument('user_ids', location='form', type=str, default='[]')
    post_parser.add_argument('group_ids', location='form', type=str, default='[]')

    delete_parser = api.parser()
    delete_parser.add_argument(
        'actions', location='form', type=str, required=True,
        help='any combination among {}'.format(str(ObjectPermissions.ACTIONS))
    )
    delete_parser.add_argument(
        'agents_set_name', location='form', type=str, required=True, choices=[Permission.GRANTED, Permission.WITHDRAWN])
    delete_parser.add_argument('user_ids', location='form', type=str, default='[]')
    delete_parser.add_argument('group_ids', location='form', type=str, default='[]')

    @api.expect(post_parser, validate=True)
    @require_oauth()
    def post(self, agent_id):
        args = self.post_parser.parse_args()

        actions = jsonify_argument(args.get('actions'), key='actions')
        check_argument_type(actions, (list, ), key='actions')

        user_ids = jsonify_argument(args.get('user_ids', None), key='user_ids') or []
        check_argument_type(user_ids, (list, ), key='user_ids')

        group_ids = jsonify_argument(args.get('group_ids', None), key='group_ids') or []
        check_argument_type(group_ids, (list, ), key='group_ids')

        def get_user_fn(user_id, projection=None):
            return users_helper.get_user(
                g.users_colln, users_helper.get_user_selector_doc(_id=user_id), projection=projection)

        def get_group_fn(group_id, projection=None):
            return groups_helper.get_group(
                g.users_colln, groups_helper.get_group_selector_doc(_id=group_id), projection=projection)

        try:
            objstore_helper.add_to_permissions_agent_set(
                g.users_colln, agent_id, current_token.user_id, current_token.group_ids,
                actions, args['agents_set_name'], get_user_fn, get_group_fn,
                user_ids=user_ids, group_ids=group_ids)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        resource_json = g.users_colln.get(agent_id, projection={"permissions": 1})
        resource_permissions = resource_json['permissions']
        return resource_permissions

    @api.expect(delete_parser, validate=True)
    def delete(self, agent_id):
        if not current_token.user_id:
            return error_response(message='not authorized', code=401)
        args = self.post_parser.parse_args()

        actions = jsonify_argument(args.get('actions'), key='actions')
        check_argument_type(actions, (list, ), key='actions')

        user_ids = jsonify_argument(args.get('user_ids', None), key='user_ids') or []
        check_argument_type(user_ids, (list, ), key='user_ids')

        group_ids = jsonify_argument(args.get('group_ids', None), key='group_ids') or []
        check_argument_type(group_ids, (list, ), key='group_ids')

        try:
            objstore_helper.remove_from_permissions_agent_set(
                g.users_colln, agent_id, current_token.user_id, current_token.group_ids,
                actions, args['agents_set_name'],
                user_ids=user_ids, group_ids=group_ids)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        agent_json = g.users_colln.get(agent_id, projection={"permissions": 1})
        agent_permissions = agent_json['permissions']
        return agent_permissions


@api.route('/agents/<string:agent_id>/resolved_permissions')
class ResolvedPermissions(flask_restplus.Resource):

    get_parser = api.parser()
    get_parser.add_argument('actions', location='args', type=str, default=None)
    get_parser.add_argument(
        'Authorization', location='headers', type=str, required=True,
        help='should be in form of "Bearer <access_token>"'
    )

    @api.expect(get_parser, validate=True)
    @require_oauth()
    def get(self, agent_id):
        if not current_token.user_id:
            return error_response(message='request should be on behalf of a user', code=400)
        args = self.get_parser.parse_args()

        actions = jsonify_argument(args.get('actions', None), key='actions') or list(ObjectPermissions.ACTIONS)
        check_argument_type(actions, (list, ), key='actions')

        agent = objstore_helper.get_resource(
            g.users_colln, agent_id, projection=None
        )
        if not agent:
            return error_response(message='resource not found', code=404)

        resolved_permissions = dict(
            (
                action,
                PermissionResolver.resolve_permission(
                    agent, action, current_token.user_id, current_token.group_ids, g.users_colln, true_if_none=False)
            )
            for action in actions
        )
        return resolved_permissions
