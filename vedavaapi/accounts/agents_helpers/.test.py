import json

from sanskrit_ld.schema.base import ObjectPermissions
from sanskrit_ld.schema.users import *
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.helpers import permissions_helper
from sanskrit_ld.helpers.permissions_helper import PermissionResolver
import bcrypt


ROOT_ADMIN = User()
permissions = ObjectPermissions.template_object_permissions()
ROOT_ADMIN.set_details(
    user_name='VEDAVAAPI_ROOT_ADMIN', hashed_password=bcrypt.hashpw('@utoDump1'.encode('utf8'), bcrypt.gensalt()).decode('utf8'), agent_class='Person', permissions=permissions)
ROOT_ADMIN._id = 'ROOT_ADMIN'
ROOT_ADMIN.validate()
for action in ObjectPermissions.ACTIONS:
    # noinspection PyUnresolvedReferences
    ROOT_ADMIN.permissions.__getattribute__(action).__getattribute__('granted').__getattribute__('users').append(ROOT_ADMIN._id)
# noinspection PyUnresolvedReferences
ROOT_ADMIN.permissions.delete.granted.users = []
# noinspection PyUnresolvedReferences
ROOT_ADMIN.permissions.delete.withdrawn.users = [ROOT_ADMIN._id]
ROOT_ADMIN.to_json_map()

ALL_USERS = UsersGroup()
permissions = ObjectPermissions.template_object_permissions()
ALL_USERS.set_details(description='all vedavaapi users', name='All Users', agent_class='Group', creator=ROOT_ADMIN._id, permissions=permissions)
ALL_USERS._id = 'ALL_USERS'
ALL_USERS.validate()

for action in ObjectPermissions.ACTIONS:
    # noinspection PyUnresolvedReferences
    ALL_USERS.permissions.__getattribute__(action).__getattribute__('granted').__getattribute__('users').append(ROOT_ADMIN._id)

# noinspection PyProtectedMember,PyUnresolvedReferences
ALL_USERS.permissions.read.granted.groups.append(ALL_USERS._id)
ALL_USERS.to_json_map()


ROOT_ADMINS = UsersGroup()
permissions = ObjectPermissions.template_object_permissions()
ROOT_ADMINS.set_details(description='vedavaapi admins', name='Root Admins', agent_class='Group', creator=ROOT_ADMIN._id, permissions=permissions)
ROOT_ADMINS._id = 'ROOT_ADMINS'
ROOT_ADMINS.validate()

for action in ObjectPermissions.ACTIONS:
    # noinspection PyUnresolvedReferences
    ROOT_ADMINS.permissions.__getattribute__(action).__getattribute__('granted').__getattribute__('users').append(ROOT_ADMIN._id)

# noinspection PyProtectedMember,PyUnresolvedReferences
ROOT_ADMINS.permissions.read.granted.groups.append(ROOT_ADMINS._id)
ROOT_ADMINS.to_json_map()


print(json.dumps(ROOT_ADMIN.to_json_map(), ensure_ascii=False, indent=2))
print(json.dumps(ALL_USERS.to_json_map(), ensure_ascii=False, indent=2))
print(json.dumps(ROOT_ADMINS.to_json_map(), ensure_ascii=False, indent=2))