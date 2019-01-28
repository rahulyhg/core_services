import flask_restplus

from . import api
from ... import get_initial_agents

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
