import logging

from flask import url_for, session
from flask_oauthlib.client import OAuth
from vedavaapi.users import get_db, get_service, get_default_permissions

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

from sanskrit_data.schema.users import User, UserPermission, AuthenticationInfo


class OAuthSignIn(object):
  """An interface to be extended for supporting various oauth authentication providers.

  A simple way to understand how this is used is to see how it is called from api_v1.py.
  Important private members:
    provider_name
    service: An oauth.remote_app object, set in the subclass constructor.
  """

  providers = None

  def __init__(self, provider_name):
    self.provider_name = provider_name
    self.service = None

  def authorize(self, next_url):
    """User-agent is directed to the oauth provider website, with a standard callback url."""
    callback_url = url_for('.oauth_authorized', provider=self.provider_name,
                           _external=True)
    return self.service.authorize(callback=callback_url, state=next_url)

  def authorized_response(self):
    return self.service.authorized_response()

  @classmethod
  def get_provider(cls, provider_name, ):
    """Get the appropriate subclass to handle login.
    
    Ensures that we use singletons.
    """
    oauth_config = get_service().config["oauth"]
    if cls.providers is None:
      cls.providers = {}
      for provider_class in cls.__subclasses__():
        provider = provider_class(client_id=oauth_config[provider_name]["client_id"],
                                  client_secret=oauth_config[provider_name]["client_secret"])
        cls.providers[provider.provider_name] = provider
    return cls.providers[provider_name]

  @staticmethod
  def _get_token():
    """This method is passed as an argument to the oauth.remote_app object.
    """
    return session.get('oauth_token')

  def get_session_data(self, data):
    pass

  def get_user_data(self):
    """Use oauth token in session to get userdata from the oauth service."""
    return None

  def get_user(self):
    """Construct or look up a User object using data obtained from get_user_data()."""
    pass


class GoogleSignIn(OAuthSignIn):
  def __init__(self, client_id, client_secret):
    super(GoogleSignIn, self).__init__(provider_name="google")
    oauth = OAuth()
    self.service = oauth.remote_app(
      'google',
      consumer_key=client_id,
      consumer_secret=client_secret,
      request_token_params={
        'scope': 'email'
      },
      base_url='https://www.googleapis.com/oauth2/v1/',
      request_token_url=None,
      access_token_method='POST',
      access_token_url='https://accounts.google.com/o/oauth2/token',
      authorize_url='https://accounts.google.com/o/oauth2/auth',
    )
    self.service.tokengetter(GoogleSignIn._get_token)

  def get_session_data(self, data):
    return (
      data['access_token'],
      ''
    )

  def get_user_data(self):
    access_token = session.get('oauth_token')
    token = 'OAuth ' + access_token[0]
    headers = {b'Authorization': bytes(token.encode('utf-8'))}
    data = self.service.get(
      'https://www.googleapis.com/oauth2/v1/userinfo', None,
      headers=headers)
    return data.data

  def get_user(self):
    data = self.get_user_data()
    logging.debug(data)
    user = get_db().get_user_from_auth_info(AuthenticationInfo.from_details(auth_user_id=data['email'],
                                                                            auth_provider=self.provider_name))
    logging.debug(user)
    if user is None:
      user = User.from_details(
        auth_infos=[AuthenticationInfo.from_details(auth_user_id=data['email'], auth_provider=self.provider_name)],
        user_type="human", permissions=get_default_permissions())
    # logging.debug(user)
    return user
