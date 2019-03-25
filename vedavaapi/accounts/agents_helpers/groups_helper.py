from sanskrit_ld.helpers.permissions_helper import PermissionResolver
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.base import ObjectPermissions
from sanskrit_ld.schema.users import UsersGroup
from vedavaapi.objectdb.helpers import projection_helper, ObjModelException, objstore_helper


def get_group_selector_doc(_id=None, group_name=None):
    if _id is not None:
        return {"jsonClass": "UsersGroup", "_id": _id}
    elif group_name is not None:
        return {"jsonClass": "UsersGroup", "groupName": group_name}
    else:
        return None


def get_group(groups_colln, group_selector_doc, projection=None):
    projection = projection_helper.modified_projection(projection, mandatory_attrs=['jsonClass'])
    group_json = groups_colln.find_one(group_selector_doc, projection=projection)
    return JsonObject.make_from_dict(group_json)


def get_group_id(groups_colln, group_name):
    group = get_group(groups_colln, get_group_selector_doc(group_name=group_name), projection={"_id": 1})
    # noinspection PyProtectedMember
    return group._id if group else None


def get_group_hierarchy(groups_colln, group_json, groups_projection=None):
    groups_projection = projection_helper.modified_projection(
        groups_projection, mandatory_attrs=["_id", "source"]
    )

    group_hierarchy = []
    parent_group_id = group_json.get('source', None)
    if not parent_group_id:
        return group_hierarchy

    parent_group_json = groups_colln.find_one(
        get_group_selector_doc(_id=parent_group_id), projection=groups_projection)
    if parent_group_json is None:
        return group_hierarchy

    group_hierarchy.append(parent_group_json)

    parent_group_hierarchy = get_group_hierarchy(
        groups_colln, parent_group_json, groups_projection=groups_projection)
    group_hierarchy.extend(parent_group_hierarchy)

    return group_hierarchy


def get_user_groups(groups_colln, user_id, groups_projection=None):
    groups_projection = projection_helper.modified_projection(
        groups_projection, mandatory_attrs=["_id", "source"]
    )

    group_id_jsons_map = {}
    explicit_group_jsons = groups_colln.find(
        {"jsonClass": UsersGroup.json_class, "members": user_id}, projection=groups_projection
    )
    group_id_jsons_map.update(dict((group_json['_id'], group_json) for group_json in explicit_group_jsons))

    for group_json in explicit_group_jsons:
        group_hierarchy = get_group_hierarchy(groups_colln, group_json, groups_projection=groups_projection)
        group_id_jsons_map.update(dict((group_json['_id'], group_json) for group_json in group_hierarchy))

    return list(group_id_jsons_map.values())


'''
functions for creating group
'''


def insert_new_group(groups_colln, group):
    group_id = groups_colln.insert_one(group.to_json_map()).inserted_id
    return group_id


def create_new_group(groups_colln, group_json, user_id, user_group_ids, initial_agents=None, ignore_source=False):
    for k in ('_id', 'members'):
        if k in group_json:
            raise ObjModelException('you cannot set "{}" attribute.', 403)

    for k in ('groupName', 'jsonClass'):
        if k not in group_json:
            raise ObjModelException('{} should be provided for creating new group'.format(k), 400)

    if group_json['jsonClass'] != 'UsersGroup':
        raise ObjModelException('invalid jsonClass', 403)

    if not ignore_source:
        if 'source' not in group_json:
            group_json['source'] = initial_agents.all_users_group_id

    old_group = get_group(
        groups_colln, get_group_selector_doc(group_name=group_json['groupName']), projection={"_id": 1, "jsonClass": 1})
    if old_group is not None:
        raise ObjModelException('group already exists', 403)

    group = JsonObject.make_from_dict(group_json)
    # noinspection PyProtectedMember
    group.set_from_dict({"members": [user_id]})

    new_group_id = objstore_helper.create_resource(
        groups_colln, group.to_json_map(), user_id, user_group_ids,
        initial_agents=initial_agents, standalone=ignore_source)
    return new_group_id


def add_users_to_group(users_colln, group_selector_doc, user_ids, current_user_id, current_group_ids):

    group = JsonObject.make_from_dict(
        users_colln.find_one(group_selector_doc, projection={"jsonClass": 1, "_id": 1, "source": 1, "permissions": 1}))
    if group is None:
        raise ObjModelException('group not found', 404)

    if current_user_id and not PermissionResolver.resolve_permission(
            group, ObjectPermissions.UPDATE_CONTENT, current_user_id, current_group_ids, users_colln):
        raise ObjModelException('permission denied', 403)

    for user_id in user_ids:
        from . import users_helper
        user_json = users_colln.find_one(users_helper.get_user_selector_doc(_id=user_id), projection={"_id": 1})
        if user_json is None:
            raise ObjModelException('user "{}" not found'.format(user_id), 403)

    update_doc = {"$addToSet": {"members": {"$each": user_ids}}}
    response = users_colln.update_one(group_selector_doc, update_doc)

    return response.modified_count


def remove_users_from_group(users_colln, group_selector_doc, user_ids, current_user_id, current_group_ids):

    group = JsonObject.make_from_dict(
        users_colln.find_one(group_selector_doc, projection={"jsonClass": 1, "_id": 1, "source": 1, "permissions": 1}))
    if group is None:
        raise ObjModelException('group not found', 404)

    if current_user_id and not PermissionResolver.resolve_permission(
            group, ObjectPermissions.UPDATE_CONTENT, current_user_id, current_group_ids, users_colln):
        raise ObjModelException('permission denied', 403)

    update_doc = {"$pull": {"members": {"$in": user_ids}}}
    response = users_colln.update_one(group_selector_doc, update_doc)

    return response.modified_count
