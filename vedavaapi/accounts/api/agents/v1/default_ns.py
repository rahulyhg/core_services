import flask_restplus
from sanskrit_ld.schema.base import Permission, ObjectPermissions
from vedavaapi.accounts.agents_helpers import users_helper, groups_helper
from vedavaapi.common.api_common import get_current_user_id, get_current_user_group_ids, error_response, \
    jsonify_argument, check_argument_type
from vedavaapi.objectdb import objstore_helper

from . import api
from ... import get_initial_agents, get_users_colln

agents_ns = api.namespace('default', path='/', description='agents namespace')


# noinspection PyMethodMayBeStatic
@agents_ns.route('/initial_agents')
class InitialAgents(flask_restplus.Resource):

    def get(self):
        initial_agents = get_initial_agents()
        return {
            "root_admin_id": initial_agents.root_admin_id,
            "root_admins_group_id": initial_agents.root_admins_group_id,
            "all_users_group_id": initial_agents.all_users_group_id
        }


@api.route('/agents/<string:agent_id>/permitted_agents')
class PermittedAgents(flask_restplus.Resource):

    post_parser = api.parser()
    post_parser.add_argument('action', location='form', type=str, required=True, choices=ObjectPermissions.ACTIONS)
    post_parser.add_argument(
        'agents_set_name', location='form', type=str, required=True, choices=[Permission.GRANTED, Permission.WITHDRAWN])
    post_parser.add_argument('user_ids', location='form', type=str, default='[]')
    post_parser.add_argument('group_ids', location='form', type=str, default='[]')

    delete_parser = api.parser()
    delete_parser.add_argument('action', location='form', type=str, required=True, choices=ObjectPermissions.ACTIONS)
    delete_parser.add_argument(
        'agents_set_name', location='form', type=str, required=True, choices=[Permission.GRANTED, Permission.WITHDRAWN])
    delete_parser.add_argument('user_ids', location='form', type=str, default='[]')
    delete_parser.add_argument('group_ids', location='form', type=str, default='[]')

    @api.expect(post_parser, validate=True)
    def post(self, agent_id):
        colln = get_users_colln()
        current_user_id = get_current_user_id(required=True)
        current_user_group_ids = get_current_user_group_ids()
        args = self.post_parser.parse_args()

        user_ids = jsonify_argument(args.get('user_ids', None), key='user_ids') or []
        check_argument_type(user_ids, (list, ), key='user_ids')

        group_ids = jsonify_argument(args.get('group_ids', None), key='group_ids') or []
        check_argument_type(group_ids, (list, ), key='group_ids')

        def get_user_fn(user_id, projection=None):
            return users_helper.get_user(
                colln, users_helper.get_user_selector_doc(_id=user_id), projection=projection)

        def get_group_fn(group_id, projection=None):
            return groups_helper.get_group(
                colln, groups_helper.get_group_selector_doc(_id=group_id), projection=projection)

        try:
            objstore_helper.add_to_permissions_agent_set(
                colln, agent_id, current_user_id, current_user_group_ids,
                args['action'], args['agents_set_name'], get_user_fn, get_group_fn,
                user_ids=user_ids, group_ids=group_ids)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        resource_json = colln.get(agent_id, projection={"permissions": 1})
        resource_permissions = resource_json['permissions']
        return resource_permissions

    @api.expect(delete_parser, validate=True)
    def delete(self, agent_id):
        colln = get_users_colln()
        current_user_id = get_current_user_id(required=True)
        current_user_group_ids = get_current_user_group_ids()
        args = self.post_parser.parse_args()

        user_ids = jsonify_argument(args.get('user_ids', None), key='user_ids') or []
        check_argument_type(user_ids, (list, ), key='user_ids')

        group_ids = jsonify_argument(args.get('group_ids', None), key='group_ids') or []
        check_argument_type(group_ids, (list, ), key='group_ids')

        try:
            objstore_helper.remove_from_permissions_agent_set(
                colln, agent_id, current_user_id, current_user_group_ids,
                args['action'], args['agents_set_name'],
                user_ids=user_ids, group_ids=group_ids)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        agent_json = colln.get(agent_id, projection={"permissions": 1})
        agent_permissions = agent_json['permissions']
        return agent_permissions
