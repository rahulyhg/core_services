from collections import namedtuple

from authlib.specs.rfc6749.grants import ImplicitGrant
from authlib.flask.oauth2.authorization_server import AuthorizationServer as _AuthorizationServer


from .models import create_query_client_func, create_save_token_func
from .grants import AuthorizationCodeGrant, RefreshTokenGrant, PasswordGrant, ClientCredentialsGrant


class AuthorizationServer(_AuthorizationServer):

    def __init__(self, config, oauth_colln, users_colln, **kwargs):
        self.oauth_colln = oauth_colln
        self.users_colln = users_colln
        WrapperApp = namedtuple('WrapperApp', ('config'))
        app = WrapperApp(config)
        query_client = create_query_client_func(self.oauth_colln)
        save_token = create_save_token_func(self.oauth_colln)

        super(AuthorizationServer, self).__init__(app=app, query_client=query_client, save_token=save_token, **kwargs)
        self.register_grants()

    def register_grants(self):
        self.register_grant(AuthorizationCodeGrant)
        self.register_grant(RefreshTokenGrant)
        self.register_grant(PasswordGrant)
        self.register_grant(ImplicitGrant)
        self.register_grant(ClientCredentialsGrant)
