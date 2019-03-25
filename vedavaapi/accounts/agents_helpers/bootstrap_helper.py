from collections import namedtuple

from sanskrit_ld.schema import WrapperObject
from sanskrit_ld.schema.base import ObjectPermissions, AgentSet, Permission
from sanskrit_ld.helpers import permissions_helper
from sanskrit_ld.schema.oauth import OAuth2MasterConfig
from sanskrit_ld.schema.users import User, UsersGroup

from ..agents_helpers import users_helper, groups_helper
from ..oauth_server_helpers.models import OAuth2ClientModel


InitialAgents = namedtuple(
    'InitialAgents', ('root_admin_id', 'all_users_group_id', 'root_admins_group_id', 'root_client_id'))


# noinspection PyUnusedLocal,PyProtectedMember
def bootstrap_initial_agents(users_colln, oauth_colln, initial_agents_config):
    root_admin_conf = initial_agents_config['users']['root_admin']
    root_admin_id = create_root_admin(users_colln, root_admin_conf['email'], root_admin_conf['hashedPassword'])

    all_users_conf = initial_agents_config['groups']['all_users']
    all_users_group_id = create_all_users_group(users_colln, all_users_conf['group_name'], root_admin_id)

    permissions_helper.add_to_agent_set(
        users_colln, [root_admin_id], [ObjectPermissions.READ], Permission.GRANTED, group_pids=[all_users_group_id])

    root_admins_conf = initial_agents_config['groups']['root_admins']
    root_admins_group_id = create_root_admins_group(
        users_colln, root_admins_conf['group_name'], root_admin_id, all_users_group_id)

    root_oauth_client_conf = initial_agents_config['oauth_clients']['root_client']
    root_client_id = create_root_oauth_client(
        oauth_colln, root_oauth_client_conf['client_id'], root_oauth_client_conf['client_secret'],
        root_admin_id, root_oauth_client_conf.get('redirect_uris', None))

    bootstrap_oauth2_master_config(oauth_colln, root_admin_id, root_admins_group_id)

    return InitialAgents(root_admin_id, all_users_group_id, root_admins_group_id, root_client_id)


# noinspection PyProtectedMember
def create_root_admin(users_colln, email, hashed_password):
    existing_user_id = users_helper.get_user_id(users_colln, email)
    if existing_user_id is not None:
        return existing_user_id
    user = User()
    user.set_details(email=email, hashed_password=hashed_password)
    root_admin_id = users_helper.create_new_user(users_colln, user.to_json_map(), with_password=False)
    permissions_helper.add_to_agent_set(
        users_colln, [root_admin_id], ObjectPermissions.ACTIONS, Permission.GRANTED,
        user_pids=[root_admin_id], group_pids=[])
    return root_admin_id


# noinspection PyProtectedMember
def create_all_users_group(users_colln, group_name, creator_id):
    existing_group_json = users_colln.find_one(
        groups_helper.get_group_selector_doc(group_name=group_name), projection={"_id": 1})
    if existing_group_json is not None:
        return existing_group_json['_id']

    all_users_group = UsersGroup()
    all_users_group.set_details(
        group_name=group_name, source=None, name='All Users', description='all vedavaapi users', agent_class='Group')
    all_users_group_id = groups_helper.create_new_group(
        users_colln, all_users_group.to_json_map(), creator_id, [], ignore_source=True)

    permissions_helper.add_to_agent_set(
        users_colln, [all_users_group_id], [ObjectPermissions.UPDATE_CONTENT], Permission.GRANTED,
        user_pids=[creator_id])
    permissions_helper.add_to_agent_set(
        users_colln, [all_users_group_id],
        [ObjectPermissions.READ, ObjectPermissions.CREATE_CHILDREN], Permission.GRANTED,
        user_pids=[creator_id], group_pids=[all_users_group_id])
    return all_users_group_id


# noinspection PyProtectedMember
def create_root_admins_group(users_colln, group_name, creator_id, parent_group_id):
    existing_group_json = users_colln.find_one(
        groups_helper.get_group_selector_doc(group_name=group_name), projection={"_id": 1})
    if existing_group_json is not None:
        return existing_group_json['_id']

    root_admins_group = UsersGroup()
    root_admins_group.set_details(
        group_name=group_name, source=parent_group_id,
        name='Root Admins', description='Vedavaapi Admins', agent_class='Group')
    root_admins_group_id = groups_helper.create_new_group(
        users_colln, root_admins_group.to_json_map(), creator_id, [])

    permissions_helper.add_to_agent_set(
        users_colln, [root_admins_group_id], ObjectPermissions.ACTIONS, Permission.GRANTED, user_pids=[creator_id])
    return root_admins_group_id


def bootstrap_oauth2_master_config(oauth_colln, root_admin_id, root_admins_group_id):
    existing_master_config = oauth_colln.find_one({"jsonClass": OAuth2MasterConfig.json_class}, projection={"_id": 1})
    if existing_master_config:
        return existing_master_config['_id']

    oauth2_master_config = OAuth2MasterConfig()
    grant_privileges_conf = WrapperObject()

    ccg_agent_set = AgentSet.template_agent_set()
    ccg_agent_set.groups.append(root_admins_group_id)
    pw_agent_set = AgentSet.template_agent_set()
    pw_agent_set.groups.append(root_admins_group_id)

    grant_privileges_conf.set_from_dict({
        "client_credentials": ccg_agent_set,
        "password": pw_agent_set
    })

    permissions = ObjectPermissions.template_object_permissions()
    permissions.add_to_agent_set(
        [ObjectPermissions.READ, ObjectPermissions.UPDATE_CONTENT],
        Permission.GRANTED, group_pids=[root_admins_group_id])

    oauth2_master_config.set_from_dict({
        "permissions": permissions,
        "grant_privileges": grant_privileges_conf
    })
    return oauth_colln.insert_one(oauth2_master_config.to_json_map()).inserted_id


def create_root_oauth_client(oauth_colln, client_id, client_secret, user_id, redirect_uris=None):
    if OAuth2ClientModel.client_exists(oauth_colln, client_id=client_id):
        return OAuth2ClientModel.get_underscore_id(oauth_colln, client_id)
    client = OAuth2ClientModel()
    client.set_from_dict({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_types": ["authorization_code", "refresh_token", "implicit", "client_credentials", "password"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "client_secret_post",
        "redirect_uris": redirect_uris or [],
        "scope": "vedavaapi.root",
        "user_id": user_id
    })
    return oauth_colln.insert_one(client.to_json_map()).inserted_id
