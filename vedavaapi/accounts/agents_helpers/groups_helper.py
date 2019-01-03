from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.base import ObjectPermissions
from sanskrit_ld.schema.users import UsersGroup


def get_group_selector_doc(_id=None, group_name=None):
    if _id is not None:
        return {"jsonClass": "UsersGroup", "_id": _id}
    elif group_name is not None:
        return {"jsonClass": "UsersGroup", "groupName": group_name}
    else:
        return None


def get_group_json(groups_colln, _id=None, group_name=None, projection=None):
    group_selector_doc = get_group_selector_doc(_id=_id, group_name=group_name)
    if group_selector_doc is None:
        return None

    return groups_colln.find_one(group_selector_doc, projection=projection)


def get_group(groups_colln, _id=None, group_name=None, projection=None):
    group_selector_doc = get_group_selector_doc(_id=_id, group_name=group_name)
    if group_selector_doc is None:
        return None

    if projection is not None:
        if 0 in projection.values():
            projection.pop('jsonClass', None)
        else:
            projection.update({"jsonClass": 1})

    group_json = groups_colln.find_one(group_selector_doc, projection=projection)
    group = JsonObject.make_from_dict(group_json)
    return group


def get_group_id(groups_colln, group_name):
    group = get_group(groups_colln, group_name=group_name, projection={"_id": 1})
    # noinspection PyProtectedMember
    return group._id if group else None


def group_exists(groups_colln, _id=None, group_name=None):
    projection = {"_id": 1, "jsonClass": 1}
    group = get_group(groups_colln, _id=_id, group_name=group_name, projection=projection)
    return group is not None


'''
functions for creating group
'''


def insert_new_group(groups_colln, group):
    group_id = groups_colln.insert_one(group.to_json_map()).inserted_id
    return group_id


def create_new_group(
        groups_colln, group_name, creator_id, parent_group_id,
        name, description, agent_class='Group', permissions=None):

    group = UsersGroup()
    group.update_time()
    permissions = permissions or ObjectPermissions.template_object_permissions()
    group.set_details(
        group_name=group_name, creator=creator_id, source=parent_group_id,
        name=name, description=description, agent_class=agent_class, permissions=permissions
    )
    group.validate()

    return insert_new_group(groups_colln, group)
