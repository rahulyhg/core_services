import uuid

import bcrypt

from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.oauth import OAuth2MasterConfig, OAuth2Client
from vedavaapi.objectdb import objstore_helper


def get_client_selector_doc(_id=None, client_id=None):
    if _id is not None:
        selector_doc = {"jsonClass": "OAuth2Client", "_id": _id}

    elif client_id is not None:
        selector_doc = {"jsonClass": "OAuth2Client", "client_id": client_id}

    else:
        selector_doc = None

    return selector_doc



def get_client(oauth_colln, client_selector_doc, projection=None):
    projection = objstore_helper.modified_projection(projection, mandatory_attrs=["jsonClass"])
    user_json = oauth_colln.find_one(client_selector_doc, projection=projection)
    return JsonObject.make_from_dict(user_json)


def project_client_json(client_json, projection=None):
    client_exposed_projection = objstore_helper.get_restricted_projection(projection, {"client_secret": 0})
    projected_client_json = objstore_helper.project_doc(
        client_json, objstore_helper.get_restricted_projection(projection, client_exposed_projection))
    return projected_client_json


def get_client_underscore_id(oauth_colln, client_id):
    client = get_client(oauth_colln, get_client_selector_doc(client_id=client_id), projection={"_id": 1})
    # noinspection PyProtectedMember
    return client._id if client else None


"""
"""

def create_new_client(oauth_colln, client_json, client_type, user_id, group_ids, initial_agents=None):
    oauth2_master_config = oauth_colln.find_one({"jsonClass": OAuth2MasterConfig.json_class})
    if oauth2_master_config:
        grant_privileges_conf = oauth2_master_config['grant_privileges']

        cc_agent_set = grant_privileges_conf['client_credentials']
        allow_cc_grant = user_id in cc_agent_set['users'] or True in [group in cc_agent_set['groups'] for group in group_ids]

        pw_agent_set = grant_privileges_conf['password']
        allow_pw_grant = user_id in pw_agent_set['users'] or True in [group in pw_agent_set['groups'] for group in group_ids]
    else:
        allow_cc_grant = allow_pw_grant = False

    for k in ('_id', 'client_id', 'client_secret', 'token_endpoint_auth_method', 'grant_types', 'response_types', 'scope', 'user_id'):
        if k in client_json:
            raise objstore_helper.ObjModelException('you can\'t set {} attribute'.format(k), 403)

    if client_json['jsonClass'] != OAuth2Client.json_class:
        raise objstore_helper.ObjModelException('invalid jsonClass', 403)

    essential_fields = ['name']
    for k in essential_fields:
        if k not in client_json:
            raise objstore_helper.ObjModelException('unsufficient data', 403)

    client_id = uuid.uuid4().hex
    grant_types = ['authorization_code', 'refresh_token', 'implicit']
    if allow_cc_grant:
        grant_types.append('client_credentials')
    if allow_pw_grant:
        grant_types.append('password')

    client_json.update({
        "client_id": client_id,
        "token_endpoint_auth_method": "client_secret_post" if client_type != 'public' else 'none',
        "grant_types": grant_types, "response_types": ["code", "token"],
        "scope": "vedavaapi.root", "user_id": user_id
    })

    if client_type == 'private':
        client_secret = bcrypt.gensalt(24).decode('utf-8')
        client_json['client_secret'] = client_secret

    client = JsonObject.make_from_dict(client_json)

    new_client_underscore_id = objstore_helper.create_resource(oauth_colln, client, user_id, group_ids, initial_agents=initial_agents, standalone=True)
    return new_client_underscore_id
