import sys

import bcrypt

from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.users import User
from sanskrit_ld.schema.base import ObjectPermissions
from vedavaapi.objectdb.mydb import MyDbCollection


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


def get_user_json(users_colln, _id=None, email=None, external_provider=None, external_uid=None, projection=None):
    user_selector_doc = get_user_selector_doc(
        _id=_id, email=email,
        external_provider=external_provider, external_uid=external_uid)

    if user_selector_doc is None:
        return None

    return users_colln.find_one(user_selector_doc, projection=projection)


def get_user(users_colln, _id=None, email=None, external_provider=None, external_uid=None, projection=None):
    """

    :param projection:
    :type users_colln: MyDbCollection
    :param _id:
    :param email:
    :param external_provider:
    :param external_uid:
    :return:
    """
    user_selector_doc = get_user_selector_doc(
        _id=_id, email=email,
        external_provider=external_provider, external_uid=external_uid)

    if user_selector_doc is None:
        return None

    if projection is not None:
        if 0 in projection.values():
            projection.pop('jsonClass', None)
        else:
            projection.update({"jsonClass": 1})

    user_json = users_colln.find_one(user_selector_doc, projection=projection)
    user = JsonObject.make_from_dict(user_json)
    return user


# noinspection PyProtectedMember
def get_user_id(users_colln, email):
    user = get_user(users_colln, email=email, projection={"_id": 1})
    return user._id if user else None


def user_exists(users_colln, _id=None, email=None, external_provider=None, external_uid=None):
    projection = {"_id": 1, "jsonClass": 1}
    user = get_user(
        users_colln, _id=_id, email=email,
        external_provider=external_provider, external_uid=external_uid,
        projection=projection)

    return user is not None


'''
helpers over user object
purely JsonObject related operations. no db operations
'''


def has_registered(user):
    if hasattr(user, "email") and hasattr(user, "hashedPassword"):
        return True
    return False


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


def is_member(user, group_id):
    if not hasattr(user, 'target'):
        return None
    return group_id in user.target


def check_password(user, password):
    print(user.hashedPassword, password, file=sys.stderr)
    return bcrypt.checkpw(password.encode('utf-8'), user.hashedPassword.encode('utf-8'))


'''
functions for modifying existing users in collection
purely basic db operations
no validity checks.
'''


def update_user(users_colln, user_id, update_doc, return_modified_status=False):
    """

    :type users_colln: MyDbCollection
    :param user_id:
    :param update_doc:
    :param return_modified_status:
    :return:
    """
    user_selector_doc = get_user_selector_doc(_id=user_id)
    if not return_modified_status:
        return users_colln.find_one_and_update(user_selector_doc, update_doc)
    else:
        return users_colln.update_one(user_selector_doc, update_doc).modified_count > 0


def set_details(users_colln, user_id, diff, return_modified_status=False):
    update_doc = {
        "$set": diff.to_json_map() if isinstance(diff, JsonObject) else diff
    }
    return update_user(users_colln, user_id, update_doc, return_modified_status=return_modified_status)


def add_group(users_colln, user_id, group_id, return_modified_status=False):
    update_doc = {
        "$addToSet": {"target": group_id}
    }
    return update_user(users_colln, user_id, update_doc, return_modified_status=return_modified_status)


def remove_groups(users_colln, user_id, group_ids, return_modified_status=False):
    update_doc = {
        "$pull": {"target": {"$in": group_ids}}
    }
    return update_user(users_colln, user_id, update_doc, return_modified_status=return_modified_status)


def add_external_authentications(users_colln, user_id, auth_info, return_modified_status=False):
    update_doc = {
        "$addToSet": {
            "externalAuthentications": auth_info.to_json_map() if isinstance(auth_info, JsonObject) else auth_info
        }
    }
    return update_user(users_colln, user_id, update_doc, return_modified_status=return_modified_status)


def remove_external_authentications(users_colln, user_id, provider_names, return_modified_status=False):
    update_doc = {
        "$pull": {
            "externalAuthentications": {
                "provider": {"$in": provider_names}
            }
        }
    }
    return update_user(users_colln, user_id, update_doc, return_modified_status=return_modified_status)


'''
functions for creating new user in collection
'''


def insert_new_user(users_colln, user):
    user_id = users_colln.insert_one(user.to_json_map()).inserted_id
    return user_id


def create_new_user(users_colln, email, hashed_password, agent_class='Person', permissions=None):
    """

    :type users_colln: MyDbCollection
    :param email:
    :param hashed_password:
    :param agent_class:
    :param permissions:
    :return:
    """
    user = User()
    user.update_time()
    permissions = permissions or ObjectPermissions.template_object_permissions()
    user.set_details(
        email=email, hashed_password=hashed_password, agent_class=agent_class, permissions=permissions)
    user.validate()

    return insert_new_user(users_colln, user)


def create_new_external_user(users_colln, auth_info, permissions=None):
    user = User()
    user.update_time()
    permissions = permissions or ObjectPermissions.template_object_permissions()
    user.set_details(external_authentications=[auth_info], permissions=permissions)
    user.validate()

    return insert_new_user(users_colln, user)
