import sys

import bcrypt
from sanskrit_ld.helpers import permissions_helper

from sanskrit_ld.schema import JsonObject, WrapperObject
from sanskrit_ld.schema.base import ObjectPermissions
from sanskrit_ld.schema.users import User

from vedavaapi.objectdb import objstore_helper


def get_user_selector_doc(_id=None, email=None, external_provider=None, external_uid=None):
    if _id is not None:
        selector_doc = {"jsonClass": "User", "_id": _id}

    elif email is not None:
        selector_doc = {"jsonClass": "User", "email": email}

    elif external_provider is not None and external_uid is not None:
        selector_doc = {
            "jsonClass": "User",
            "externalAuthentications": {"$elemMatch": {"provider": external_provider, "uid": external_uid}}
        }
    else:
        selector_doc = None

    return selector_doc


def get_user(users_colln, user_selector_doc, projection=None):
    projection = objstore_helper.modified_projection(projection, mandatory_attrs=["jsonClass"])
    user_json = users_colln.find_one(user_selector_doc, projection=projection)
    return JsonObject.make_from_dict(user_json)


def project_user_json(user_json, projection=None):
    user_exposed_projection = objstore_helper.modified_projection(
        user_json.get('exposed_projection', None), mandatory_attrs=['_id', 'jsonClass'])
    projected_user_json = objstore_helper.project_doc(
        user_json, objstore_helper.get_restricted_projection(projection, user_exposed_projection))
    return projected_user_json


# noinspection PyProtectedMember
def get_user_id(users_colln, email):
    user = get_user(users_colln, get_user_selector_doc(email=email), projection={"_id": 1})
    return user._id if user else None


'''
helpers over user object
purely JsonObject related operations. no db operations
'''


def is_provider_linked(user, provider_name):
    """

    :type user: User
    :param provider_name:
    :return:
    """
    if not hasattr(user, 'externalAuthentications'):
        return False
    for auth_info in user.__getattribute__('externalAuthentications'):
        if auth_info.provider == provider_name:
            return True
    return False


def get_provider_uid(user, provider_name):
    """

    :type user: User
    :param provider_name:
    :return:
    """
    if not hasattr(user, 'externalAuthentications'):
        return None
    for auth_info in user.__getattribute__('externalAuthentications'):
        if auth_info.provider == provider_name:
            return auth_info.uid
    return None


def check_password(user, password):
    print(user.hashedPassword, password, file=sys.stderr)
    return bcrypt.checkpw(password.encode('utf-8'), user.hashedPassword.encode('utf-8'))


'''
functions for modifying existing users in collection
purely basic db operations
no validity checks.
'''


def create_new_user(users_colln, user_json, initial_agents=None, with_password=True):
    for k in ('_id', 'externalAuthentications'):
        if k in user_json:
            raise objstore_helper.ObjModelException('you cannot set "{}" attribute.', 403)

    essential_fields = ['email', 'jsonClass']
    if with_password:
        essential_fields.append('password')
    for k in essential_fields:
        if k not in user_json:
            raise objstore_helper.ObjModelException('{} should be provided for creating new user'.format(k), 400)

    if user_json['jsonClass'] != 'User':
        raise objstore_helper.ObjModelException('invalid jsonClass', 403)

    if with_password:
        user_json['hashedPassword'] = bcrypt.hashpw(
            user_json['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user_json.pop('password')

    existing_user = get_user(
        users_colln, get_user_selector_doc(email=user_json['email']),
        projection={"_id": 1, "jsonClass": 1})
    if existing_user is not None:
        raise objstore_helper.ObjModelException('user already exists', 403)

    user = JsonObject.make_from_dict(user_json)
    user.set_from_dict({"externalAuthentications": WrapperObject()})

    new_user_id = objstore_helper.create_resource(
        users_colln, user, None, None, initial_agents=initial_agents, standalone=True)
    permissions_helper.add_to_granted_list(
        users_colln, [new_user_id], ObjectPermissions.ACTIONS, user_pids=[new_user_id])

    from ..agents_helpers import groups_helper
    if initial_agents is not None:
        groups_helper.add_users_to_group(
            users_colln,
            groups_helper.get_group_selector_doc(_id=initial_agents.all_users_group_id), [new_user_id], None, None)

    return new_user_id


def add_external_authentication(users_colln, user_selector_doc, auth_info):
    update_doc = {
        "$set": {
            "externalAuthentications.{}".format(auth_info.provider):
                auth_info.to_json_map() if isinstance(auth_info, JsonObject) else auth_info
        }
    }
    response = users_colln.update_one(user_selector_doc, update_doc)
    return response.modified_count


def remove_external_authentication(users_colln, user_selector_doc, provider_name):
    update_doc = {
        "$unset": dict(('externalAuthentications.{}'.format(p), '') for p in [provider_name])
    }
    response = users_colln.update_one(user_selector_doc, update_doc)
    return response.modified_count
