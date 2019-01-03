import bcrypt
from sanskrit_ld.schema import JsonObject, WrapperObject
from sanskrit_ld.schema.base import ObjectPermissions

from sanskrit_ld.schema.users import User as _User
from sanskrit_ld.schema.users import UsersGroup as _UserGroup


# noinspection PyProtectedMember
class User(_User):

    def __getattribute__(self, item):
        return super(User, self).__getattribute__(item)

    @classmethod
    def cast(cls, user):
        if user is None:
            return
        user.__class__ = cls

    @classmethod
    def get_user_selector_doc(cls, _id=None, email=None):
        if _id is not None:
            selector_doc = {"jsonClass": "User", "_id": _id}

        elif email is not None:
            selector_doc = {"jsonClass": "User", "email": email}

        else:
            selector_doc = None
        return selector_doc

    @classmethod
    def get_user_json(cls, users_colln, _id=None, email=None, projection=None):
        user_selector_doc = cls.get_user_selector_doc(_id=_id, email=email)
        if user_selector_doc is None:
            return None

        return users_colln.find_one(user_selector_doc, projection=projection)

    @classmethod
    def get_user(cls, users_colln, _id=None, email=None, projection=None):
        user_selector_doc = cls.get_user_selector_doc(_id=_id, email=email)
        if user_selector_doc is None:
            return None

        if projection is not None:
            if 0 in projection.values():
                projection.pop('jsonClass', None)
            else:
                projection.update({"jsonClass": 1})

        user_json = users_colln.find_one(user_selector_doc, projection=projection)
        user = JsonObject.make_from_dict(user_json)
        cls.cast(user)
        return user

    @classmethod
    def get_underscore_id(cls, users_colln, email):
        user = cls.get_user(users_colln, email=email, projection={"_id": 1})
        return user._id if user else None

    @classmethod
    def user_exists(cls, users_colln, _id=None, email=None):
        projection = {"_id": 1, "jsonClass": 1}
        user = cls.get_user(
            users_colln, _id=_id, email=email,
            projection=projection)

        return user is not None

    @classmethod
    def update_user(cls, users_colln, user_selector_doc, update_doc, return_user=False):
        if return_user:
            user = JsonObject.make_from_dict(users_colln.find_one_and_update(user_selector_doc, update_doc))
            cls.cast(user)
            return user
        else:
            return users_colln.update_one(user_selector_doc, update_doc).modified_count > 0

    @classmethod
    def update_details(cls, users_colln, user_selector_doc, diff, return_user=False):
        update_doc = {
            "$set": diff.to_json_map() if isinstance(diff, JsonObject) else diff
        }
        return cls.update_user(users_colln, user_selector_doc, update_doc, return_user=return_user)

    @classmethod
    def add_group(cls, users_colln, user_selector_doc, group_id, return_user=False):
        update_doc = {
            "$addToSet": {"target": group_id}
        }
        return cls.update_user(users_colln, user_selector_doc, update_doc, return_user=return_user)

    @classmethod
    def remove_groups(cls, users_colln, user_selector_doc, group_ids, return_user=False):
        update_doc = {
            "$pull": {"target": {"$in": group_ids}}
        }
        return cls.update_user(users_colln, user_selector_doc, update_doc, return_user=return_user)

    @classmethod
    def add_external_authentications(cls, users_colln, user_selector_doc, auth_info, return_user=False):
        update_doc = {
            "$set": {
                "externalAuthentications.{}".format(auth_info.provider):
                    auth_info.to_json_map() if isinstance(auth_info, JsonObject) else auth_info
            }
        }
        return cls.update_user(users_colln, user_selector_doc, update_doc, return_user=return_user)

    @classmethod
    def remove_external_authentications(cls, users_colln, user_selector_doc, provider_names, return_user=False):
        update_doc = {
            "$unset": dict(('externalAuthentications.{}'.format(p), '') for p in provider_names)
        }
        return cls.update_user(users_colln, user_selector_doc, update_doc, return_user=return_user)

    @classmethod
    def insert_new_user(cls, users_colln, user):
        user_id = users_colln.insert_one(user.to_json_map()).inserted_id
        return user_id

    @classmethod
    def swizzle(cls, user):
        if hasattr(user, 'password'):
            user.hashedPassword = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            del user.password

    @classmethod
    def create_new_user(cls, users_colln, doc):
        user = JsonObject.make_from_dict(doc) if not isinstance(doc, JsonObject) else doc
        for f in ['_id', 'creator', 'created', 'permissions', 'target']:
            if hasattr(user, f):
                delattr(user, f)

        cls.swizzle(user)

        user.update_time()
        user.set_from_dict({"externalAuthentications": WrapperObject()})
        permissions = ObjectPermissions.template_object_permissions()
        user.set_details(permissions=permissions)
        user.validate()

        return cls.insert_new_user(users_colln, user)

    def get_user_id(self):
        # for oauth modelling
        return self.email

    def is_registered(self):
        if hasattr(self, 'email') and hasattr(self, 'hashedPassword'):
            return True
        return False

    def is_provider_linked(self, provider_name):
        if not hasattr(self, 'externalAuthentications'):
            return False
        for auth_info in getattr(self, 'externalAuthentications'):
            if auth_info.provider == provider_name:
                return True

        return False

    def get_provider_uid(self, provider_name):
        if not hasattr(self, 'externalAuthentications'):
            return None
        for auth_info in getattr(self, 'externalAuthentications'):
            if auth_info.provider == provider_name:
                return auth_info.uid

        return None

    def is_member(self, group_id):
        if not hasattr(self, 'target'):
            return None
        return group_id in self.target

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.hashedPassword.encode('utf-8'))


class UserGroup(_UserGroup):

    def __getattribute__(self, item):
        return super(UserGroup, self).__getattribute__(item)

    @classmethod
    def cast(cls, user):
        if user is None:
            return
        user.__class__ = cls

    @classmethod
    def get_group_selector_doc(cls, _id=None, group_name=None):
        if _id is not None:
            return {"jsonClass": "UsersGroup", "_id": _id}
        elif group_name is not None:
            return {"jsonClass": "UsersGroup", "groupName": group_name}
        else:
            return None

    @classmethod
    def get_group_json(cls, groups_colln, _id=None, group_name=None, projection=None):
        group_selector_doc = cls.get_group_selector_doc(_id=_id, group_name=group_name)
        if group_selector_doc is None:
            return None

        return groups_colln.find_one(group_selector_doc, projection=projection)

    @classmethod
    def get_group(cls, groups_colln, _id=None, group_name=None, projection=None):
        group_selector_doc = cls.get_group_selector_doc(_id=_id, group_name=group_name)
        if group_selector_doc is None:
            return None

        if projection is not None:
            if 0 in projection.values():
                projection.pop('jsonClass', None)
            else:
                projection.update({"jsonClass": 1})

        group_json = groups_colln.find_one(group_selector_doc, projection=projection)
        group = JsonObject.make_from_dict(group_json)
        cls.cast(group)
        return group

    @classmethod
    def get_underscore_id(cls, groups_colln, group_name):
        group = cls.get_group(groups_colln, group_name=group_name, projection={"_id": 1})
        # noinspection PyProtectedMember
        return group._id if group else None

    @classmethod
    def group_exists(cls, groups_colln, _id=None, group_name=None):
        projection = {"_id": 1, "jsonClass": 1}
        group = cls.get_group(groups_colln, _id=_id, group_name=group_name, projection=projection)
        return group is not None

    @classmethod
    def update_group(cls, users_colln, group_selector_doc, update_doc, return_group=False):
        if return_group:
            user = JsonObject.make_from_dict(users_colln.find_one_and_update(group_selector_doc, update_doc))
            cls.cast(user)
            return user
        else:
            return users_colln.update_one(group_selector_doc, update_doc).modified_count > 0

    @classmethod
    def update_details(cls, users_colln, group_selector_doc, diff, return_group=False):
        update_doc = {
            "$set": diff.to_json_map() if isinstance(diff, JsonObject) else diff
        }
        return cls.update_group(users_colln, group_selector_doc, update_doc, return_group=return_group)

    @classmethod
    def insert_new_group(cls, groups_colln, group):
        group_id = groups_colln.insert_one(group.to_json_map()).inserted_id
        return group_id

    @classmethod
    def create_new_group(cls, groups_colln, doc, creator_pid):
        group = JsonObject.make_from_dict(doc) if not isinstance(doc, JsonObject) else doc
        for f in ['creator', 'created', 'permissions']:
            if hasattr(group, f):
                delattr(group, f)

        group.update_time()
        permissions = ObjectPermissions.template_object_permissions()
        group.set_details(permissions=permissions, creator=creator_pid)
        group.validate()

        return cls.insert_new_group(groups_colln, group)
