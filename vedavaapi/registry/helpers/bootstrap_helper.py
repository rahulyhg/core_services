from sanskrit_ld.schema.services import VedavaapiServicesRegistry
from sanskrit_ld.schema.base import ObjectPermissions

from vedavaapi.common.helpers.api_helper import get_initial_agents


def bootstrap_registry(colln, org_name):
    registry_resource = colln.find_one(
        {"jsonClass": VedavaapiServicesRegistry.json_class}, projection={"_id": 1})
    if registry_resource is not None:
        return registry_resource['_id']

    initial_agents = get_initial_agents(org_name=org_name)
    registry = VedavaapiServicesRegistry()
    registry.permissions = ObjectPermissions.template_object_permissions()

    registry.permissions.add_to_granted_list(ObjectPermissions.ACTIONS, group_pids=[initial_agents.root_admins_group_id])
    registry.permissions.add_to_granted_list(
        [ObjectPermissions.READ, ObjectPermissions.LIST], group_pids=[initial_agents.all_users_group_id])

    return colln.insert_one(registry.to_json_map())
