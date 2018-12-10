from sanskrit_ld.schema.users import User, AuthenticationInfo
from vedavaapi.objectdb.mydb import MyDbCollection


class UsersDbHelper(object):

    @classmethod
    def get_user_from_auth_info(cls, colln, auth_info):
        """

        :type auth_info: AuthenticationInfo
        :type colln: MyDbCollection
        """
        user_dict = colln.find_one({
            "authentication_infos.user_id": auth_info.user_id,
            "authentication_infos.provider": auth_info.provider,
        })
        if user_dict is None:
            return None
        user = User.make_from_dict(user_dict)
        return user

    @classmethod
    def get_matching_users_by_auth_infos(cls, colln, user):
        """

        :type user: User
        :type colln: MyDbCollection
        """
        # Check to see if there are other entries in the database with identical authentication info.
        matching_users = []
        # noinspection PyUnresolvedReferences
        for auth_info in user.authentication_infos:
            matching_user = cls.get_user_from_auth_info(colln, auth_info=auth_info)
            if matching_user is not None:
                matching_users.append(matching_user)

        return matching_users

    @classmethod
    def get_user_by_id(cls, colln, _id):
        user_dict = colln.find_one({
            "_id": _id
        })
        return user_dict
