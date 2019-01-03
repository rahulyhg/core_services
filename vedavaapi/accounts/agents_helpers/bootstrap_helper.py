from collections import namedtuple

from sanskrit_ld.schema.base import ObjectPermissions
from sanskrit_ld.helpers import permissions_helper

from .models import User, UserGroup
from ..oauth_server_helpers.models import OAuth2ClientModel


InitialAgents = namedtuple(
    'InitialAgents', ('root_admin_id', 'all_users_group_id', 'root_admins_group_id', 'root_client_id'))


# noinspection PyUnusedLocal,PyProtectedMember
def bootstrap_initial_agents(users_colln, oauth_colln, initial_agents_config):
    root_admin_conf = initial_agents_config['users']['root_admin']
    root_admin_id = create_root_admin(users_colln, root_admin_conf['email'], root_admin_conf['hashedPassword'])

    all_users_conf = initial_agents_config['groups']['all_users']
    all_users_group_id = create_all_users_group(users_colln, all_users_conf['group_name'], root_admin_id)
    User.add_group(users_colln, User.get_user_selector_doc(_id=root_admin_id), all_users_group_id)

    root_admins_conf = initial_agents_config['groups']['root_admins']
    root_admins_group_id = create_root_admins_group(users_colln, root_admins_conf['group_name'], root_admin_id)
    User.add_group(users_colln, User.get_user_selector_doc(_id=root_admin_id), root_admins_group_id)

    root_oauth_client_conf = initial_agents_config['oauth_clients']['root_client']
    root_client_id = create_root_oauth_client(
        oauth_colln, root_oauth_client_conf['client_id'], root_oauth_client_conf['client_secret'],
        root_admin_id, root_oauth_client_conf.get('redirect_uris', None))

    return InitialAgents(root_admin_id, all_users_group_id, root_admins_group_id, root_client_id)


# noinspection PyProtectedMember
def create_root_admin(users_colln, email, hashed_password):
    if User.user_exists(users_colln, email=email):
        return User.get_underscore_id(users_colln, email=email)
    user = User()
    user.set_details(email=email, hashed_password=hashed_password)
    root_admin_id = User.create_new_user(users_colln, user)
    permissions_helper.add_to_granted_list(
        users_colln, [root_admin_id], ObjectPermissions.ACTIONS, user_pids=[root_admin_id], group_pids=[])
    return root_admin_id


# noinspection PyProtectedMember
def create_all_users_group(users_colln, group_name, creator_id):
    if UserGroup.group_exists(users_colln, group_name=group_name):
        return UserGroup.get_underscore_id(users_colln, group_name)

    all_users_group = UserGroup()
    all_users_group.set_details(
        group_name=group_name, source=None, name='All Users', description='all vedavaapi users', agent_class='Group')
    all_users_group_id = UserGroup.create_new_group(
        users_colln, all_users_group, creator_id)

    permissions_helper.add_to_granted_list(
        users_colln, [all_users_group_id], ObjectPermissions.ACTIONS, user_pids=[creator_id])
    permissions_helper.add_to_granted_list(
        users_colln, [all_users_group_id], [ObjectPermissions.LINK_FROM_OTHERS], user_pids=['.*'])
    return all_users_group_id


# noinspection PyProtectedMember
def create_root_admins_group(users_colln, group_name, creator_id):
    if UserGroup.group_exists(users_colln, group_name=group_name):
        return UserGroup.get_underscore_id(users_colln, group_name)

    root_admins_group = UserGroup()
    root_admins_group.set_details(
        group_name=group_name, source=None, name='Root Admins', description='Vedavaapi Admins', agent_class='Group')
    root_admins_group_id = UserGroup.create_new_group(
        users_colln, root_admins_group, creator_id)

    permissions_helper.add_to_granted_list(
        users_colln, [root_admins_group_id], ObjectPermissions.ACTIONS, user_pids=[creator_id])
    return root_admins_group_id


def create_root_oauth_client(oauth_colln, client_id, client_secret, user_id, redirect_uris=None):
    if OAuth2ClientModel.client_exists(oauth_colln, client_id=client_id):
        return OAuth2ClientModel.get_underscore_id(oauth_colln, client_id)
    client = OAuth2ClientModel()
    client.set_from_dict({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_types": ["authorization_code", "implicit", "client_credentials", "password"],
        "response_types": ["code", "token"],
        "token_endpoint_auth_method": "client_secret_post",
        "redirect_uris": redirect_uris or [],
        "scope": "vedavaapi.root",
        "user_id": user_id
    })
    return oauth_colln.insert_one(client.to_json_map()).inserted_id
