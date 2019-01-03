import sys
import time

from authlib.specs.rfc6749 import grants
from werkzeug.security import gen_salt

from vedavaapi.objectdb.mydb import MyDbCollection

from .models import (
    get_json_object,
    UserModel)
from .models import (
    OAuth2AuthorizationCodeModel,
    OAuth2TokenModel
)
from ..agents_helpers import users_helper


# noinspection PyProtectedMember
class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):

    def __init__(self, request, server):
        super(AuthorizationCodeGrant, self).__init__(request, server)
        self.oauth_colln = self.server.oauth_colln  # type: MyDbCollection
        self.users_colln = self.server.users_colln  # type: MyDbCollection

    def create_authorization_code(self, client, grant_user, request):
        authorization_code_doc = {
            "client_id": client.client_id,
            "redirect_uri": request.redirect_uri,
            "scope": request.scope,
            "user_id": grant_user._id,
        }
        existing_item = get_json_object(self.oauth_colln, authorization_code_doc, cast_class=OAuth2AuthorizationCodeModel)
        if existing_item and not existing_item.is_expired():
            return existing_item.code

        item = OAuth2AuthorizationCodeModel()
        item.set_from_dict(authorization_code_doc)
        item.set_from_dict({"code": gen_salt(48), "auth_time": time.time()})
        item.validate()
        self.oauth_colln.insert_one(item.to_json_map())
        return item.code

    def parse_authorization_code(self, code, client):
        query_doc = {"jsonClass": "OAuth2AuthorizationCode", "code": code, "client_id": client.client_id}
        item = get_json_object(
            self.oauth_colln, query_doc, cast_class=OAuth2AuthorizationCodeModel)  # type: OAuth2AuthorizationCodeModel

        if item and not item.is_expired():
            return item

    def delete_authorization_code(self, authorization_code):
        selector_doc = {"jsonClass": "OAuth2AuthorizationCode", "_id": authorization_code._id}
        self.oauth_colln.delete_one(selector_doc)

    def authenticate_user(self, authorization_code):
        user = users_helper.get_user(self.users_colln, _id=authorization_code.user_id)
        UserModel.cast(user)
        return user


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):

    def __init__(self, request, server):
        super(PasswordGrant, self).__init__(request, server)
        self.oauth_colln = self.server.oauth_colln
        self.users_colln = self.server.users_colln

    def authenticate_user(self, username, password):
        user = users_helper.get_user(self.users_colln, email=username)
        UserModel.cast(user)
        if user.check_password(password):
            return user


class RefreshTokenGrant(grants.RefreshTokenGrant):

    def __init__(self, request, server):
        super(RefreshTokenGrant, self).__init__(request, server)
        self.oauth_colln = self.server.oauth_colln
        self.users_colln = self.server.users_colln

    def authenticate_refresh_token(self, refresh_token):
        query_doc = {"jsonClass": "OAuth2Token", "refresh_token": refresh_token}
        item = get_json_object(self.oauth_colln, query_doc, cast_class=OAuth2TokenModel)  # type: OAuth2TokenModel

        if item and not item.is_refresh_token_expired():
            return item

    def authenticate_user(self, credential):
        user = users_helper.get_user(self.users_colln, _id=credential.user_id)
        UserModel.cast(user)
        return user
