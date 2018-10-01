from sanskrit_data.schema.users import User


class UsersDbHelper(object):

    @classmethod
    def get_user_from_auth_info(cls, colln, auth_info):
        user_dict = colln.find_one({"authentication_infos.auth_user_id": auth_info.auth_user_id,
                                               "authentication_infos.auth_provider": auth_info.auth_provider,
                                                })
        if user_dict is None:
            return None
        user = User.make_from_dict(user_dict)
        return user

    @classmethod
    def get_matching_users_by_auth_infos(cls, colln, user):
        # Check to see if there are other entries in the database with identical authentication info.
        matching_users = []
        for auth_info in user.authentication_infos:
            matching_user = cls.get_user_from_auth_info(colln, auth_info=auth_info)
            if matching_user is not None:
                matching_users.append(matching_user)

        return matching_users

