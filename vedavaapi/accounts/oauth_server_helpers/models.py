import bcrypt
import time

from authlib.specs.rfc6749.models import ClientMixin, AuthorizationCodeMixin, TokenMixin
from sanskrit_ld.schema import JsonObject

from sanskrit_ld.schema.oauth import OAuth2Client, OAuth2AuthorizationCode, OAuth2Token
from sanskrit_ld.schema.users import User
from vedavaapi.objectdb.mydb import MyDbCollection


class OAuth2BaseModel(object):

    @classmethod
    def cast(cls, obj):
        if obj is None:
            return
        obj.__class__ = cls


class UserModel(OAuth2BaseModel, User):

    def __getattr__(self, item):
        return object.__getattribute__(self, item)

    def get_user_id(self):
        return self._id

    def check_password(self, password):
        if not hasattr(self, 'hashedPassword'):
            return False
        if not bcrypt.checkpw(password.encode('utf-8'), self.hashedPassword.encode('utf-8')):
            return False
        return True


class OAuth2ClientModel(OAuth2BaseModel, ClientMixin, OAuth2Client):

    def __getattr__(self, item):
        return object.__getattribute__(self, item)

    @property
    def client_metadata(self):
        keys = [
            'redirect_uris', 'token_endpoint_auth_method', 'grant_types',
            'response_types', 'client_name', 'client_uri', 'logo_uri',
            'scope', 'contacts', 'tos_uri', 'policy_uri', 'jwks_uri', 'jwks',
        ]
        metadata = {k: getattr(self, k) for k in keys if hasattr(self, k)}
        return metadata

    @client_metadata.setter
    def client_metadata(self, value):
        for k in value:
            if hasattr(self, k):
                setattr(self, k, value[k])

    @property
    def client_info(self):
        return dict(
            client_id=getattr(self, 'client_id', None),
            client_secret=getattr(self, 'client_secret', None),
            client_id_issued_at=getattr(self, 'issued_at', None),
            client_secret_expires_at=getattr(self, 'expires_at', None)
        )

    @classmethod
    def get_client_selector_doc(cls, _id=None, client_id=None):
        if _id is not None:
            selector_doc = {"jsonClass": "OAuth2Client", "_id": _id}

        elif client_id is not None:
            selector_doc = {"jsonClass": "OAuth2Client", "client_id": client_id}

        else:
            selector_doc = None

        return selector_doc

    @classmethod
    def get_client(cls, oauth_colln, _id=None, client_id=None, projection=None):
        client_selector_doc = cls.get_client_selector_doc(_id=_id, client_id=client_id)

        if client_selector_doc is None:
            return None

        if projection is not None:
            if 0 in projection.values():
                projection.pop('jsonClass', None)
            else:
                projection.update({"jsonClass": 1})

        client_json = oauth_colln.find_one(client_selector_doc, projection=projection)
        client = JsonObject.make_from_dict(client_json)
        return client

    @classmethod
    def get_underscore_id(cls, oauth_colln, client_id):
        client = cls.get_client(oauth_colln, client_id=client_id, projection={"_id": 1})
        # noinspection PyProtectedMember
        return client._id if client else None

    @classmethod
    def client_exists(cls, oauth_colln, _id=None, client_id=None):
        projection = {"_id": 1, "jsonClass": 1}
        client = cls.get_client(oauth_colln, _id=_id, client_id=client_id, projection=projection)

        return client is not None

    @classmethod
    def insert_new_client(cls, oauth_colln, client):
        client_id = oauth_colln.insert_one(client.to_json_map())
        return client_id

    def get_client_id(self):
        return self.client_id

    def get_default_redirect_uri(self):
        if hasattr(self, 'redirect_uris'):
            return self.redirect_uris[0]

    def check_redirect_uri(self, redirect_uri):
        if not hasattr(self, 'redirect_uris'):
            return False
        return redirect_uri in self.redirect_uris

    def has_client_secret(self):
        return hasattr(self, 'client_secret')

    def check_token_endpoint_auth_method(self, method):
        if not hasattr(self, 'token_endpoint_auth_method'):
            return False
        return self.token_endpoint_auth_method == method

    def check_response_type(self, response_type):
        if not hasattr(self, 'response_types'):
            return False
        return response_type in self.response_types

    def check_grant_type(self, grant_type):
        if not hasattr(self, 'grant_types'):
            return False
        return grant_type in self.grant_types

    def check_requested_scopes(self, scopes):
        if not hasattr(self, 'scope'):
            return False
        allowed = set(self.scope.split())
        return allowed.issuperset(set(scopes))

    def check_client_secret(self, client_secret):
        if not hasattr(self, 'client_secret'):
            return False
        return self.client_secret == client_secret


class OAuth2AuthorizationCodeModel(OAuth2BaseModel, AuthorizationCodeMixin, OAuth2AuthorizationCode):

    def __getattr__(self, item):
        return object.__getattribute__(self, item)

    def is_expired(self):
        return self.auth_time + 300 < time.time()

    def get_redirect_uri(self):
        return getattr(self, 'redirect_uri', None)

    def get_scope(self):
        return getattr(self, 'scope', None)

    def get_auth_time(self):
        return getattr(self, 'auth_time', None)


class OAuth2TokenModel(OAuth2BaseModel, TokenMixin, OAuth2Token):

    def __getattr__(self, item):
        return object.__getattribute__(self, item)

    def get_scope(self):
        return getattr(self, 'scope', None)

    def get_expires_in(self):
        return getattr(self, 'expires_in', None)

    def get_expires_at(self):
        return self.issued_at + self.expires_in

    def is_refresh_token_expired(self):
        expires_at = self.issued_at + self.expires_in * 2
        return expires_at < time.time()


def get_json_object(colln, query_doc, projection=None, cast_class=None):
    item_json = colln.find_one(query_doc, projection=projection)
    item = JsonObject.make_from_dict(item_json)
    cast_class.cast(item)
    return item


def create_query_client_func(oauth_colln):
    """

    :type oauth_colln: MyDbCollection
    :return:
    """

    def query_client(client_id):
        query_doc = {
            "jsonClass": "OAuth2Client",
            "client_id": client_id
        }
        return get_json_object(oauth_colln, query_doc, cast_class=OAuth2ClientModel)

    return query_client


def create_save_token_func(oauth_colln):
    """

    :type oauth_colln: MyDbCollection
    :return:
    """

    def save_token(token, request):
        if request.user:
            user_id = request.user._id
        else:
            user_id = None

        client = request.client

        item = OAuth2TokenModel()
        item.set_from_dict({
            "client_id": client.client_id,
            "user_id": user_id,
            "issued_at": time.time()
        })
        item.set_from_dict(dict(**token))
        item.validate()
        oauth_colln.insert_one(item.to_json_map())

    return save_token


def create_query_token_func(oauth_colln):

    def query_token(token, token_type_hint, client):

        query_doc = {
            "jsonClass": "OAuth2Token",
            "client_id": client.client_id,
            "revoked": False
        }
        if token_type_hint == 'access_token':
            query_doc.update({"access_token": token})
            return get_json_object(oauth_colln, query_doc, cast_class=OAuth2TokenModel)
        elif token_type_hint == 'refresh_token':
            query_doc.update({"refresh_token": token})
            return get_json_object(oauth_colln, query_doc, cast_class=OAuth2TokenModel)

        # without token_type_hint
        query_doc.update({"access_token": token})
        item = get_json_object(oauth_colln, query_doc, cast_class=OAuth2TokenModel)
        if item is not None:
            return item

        query_doc.pop('access_token', None)
        query_doc.update({"refresh_token": token})
        return get_json_object(oauth_colln, query_doc, cast_class=OAuth2TokenModel)

    return query_token


def create_revocation_endpoint(oauth_colln):
    """

    :type oauth_colln: MyDbCollection
    :return:
    """
    from authlib.specs.rfc7009 import RevocationEndpoint
    query_token = create_query_token_func(oauth_colln)

    class _RevocationEndpoint(RevocationEndpoint):
        def query_token(self, token, token_type_hint, client):
            return query_token(token, token_type_hint, client)

        def revoke_token(self, token):
            # noinspection PyProtectedMember
            selector_doc = {
                "jsonClass": "OAuth2Token",
                "_id": token._id
            }
            update_toc = {
                "revoked": True
            }
            oauth_colln.update_one(selector_doc, update_toc)

    return _RevocationEndpoint


def create_bearer_token_validator(oauth_colln):
    """

    :type oauth_colln: MyDbCollection
    :return:
    """
    from authlib.specs.rfc6750 import BearerTokenValidator

    class _BearerTokenValidator(BearerTokenValidator):

        def authenticate_token(self, token_string):
            query_doc = {
                "jsonClass": "OAuth2Token",
                "access_token": token_string
            }
            return get_json_object(oauth_colln, query_doc, cast_class=OAuth2TokenModel)

        def request_invalid(self, request):
            return False

        def token_revoked(self, token):
            return getattr(token, 'revoked', False)

    return _BearerTokenValidator
