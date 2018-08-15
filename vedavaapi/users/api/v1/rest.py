import logging

import flask_restplus, flask
from flask import session, request, Response
from furl import furl
from jsonschema import ValidationError
from sanskrit_data.schema.common import JsonObject
import sanskrit_data.schema.common as common_data_containers
from sanskrit_data.schema.users import AuthenticationInfo, User

from ..v1 import api
from .oauth import OAuthClient, GoogleClient
from ... import get_db, get_default_permissions, myservice


def redirect_js(next_url):
  return 'Continue on to <a href="%(url)s">%(url)s</a>. <script>window.location = "%(url)s";</script>' % {"url": next_url}

@api.route('/oauth_login/<string:provider_name>')
class OauthLogin(flask_restplus.Resource):
    get_parser = api.parser()
    get_parser.add_argument('next_url', type=str, location='args')

    @api.expect(get_parser, validate=True)
    def get(self, provider_name):
        client = OAuthClient.get_client_for_provider(provider_name)
        if not client:
            return {'error' : {'message' : 'currently oauth provider with name "{provider_name}" not supported.'.format(provider_name=provider_name)}}, 400
        return client.redirect_for_authorization(next_url=flask.request.args.get('next_url'))


@api.route('/oauth_authorized/<string:provider_name>')
class OauthAuthorized(flask_restplus.Resource):
    get_parser = api.parser()
    get_parser.add_argument('state', type=str, location='args')

    @api.expect(get_parser, validate=True)
    @api.doc(responses={
        200: 'Login success.',
        401: 'Unauthorized.',
    })
    def get(self, provider_name):
        client = OAuthClient.get_client_for_provider(provider_name)
        if not client:
            return {'error' : {'message' : 'currently oauth provider with name "{provider_name}" not supported.'.format(provider_name=provider_name)}}, 400
        auth_code = client.extract_auth_code()
        access_token_response = client.exchange_code_for_access_token(auth_code)
        userinfo, response_code = client.get_user_info(access_token_response=access_token_response)
        if 'error' in userinfo:
            #TODO should return/redirect to a custom error page instead.
            return {'error' : 'error in authenticating'}, 401

        #provider agnostic key value format with data extracted.
        userinfo_standard = client.user_info_in_standard_format(userinfo)

        session['oauth_token'] = client.extract_access_token_from_response(access_token_response)
        session['user'] = get_user(userinfo_standard, client.name).to_json_map()

        next_url = request.args.get('state')
        if next_url is not None:
            next_url_final = furl(next_url)
            next_url_final.args["response_code"] = response_code
            from flask import Response
            return Response(redirect_js(next_url_final))
        else:
            return {"message": "Did not get a next_url, it seems!"}, response_code



def get_user(userinfo, provider_name):
    user = get_db().get_user_from_auth_info(
        AuthenticationInfo.from_details(auth_user_id=userinfo['email'], auth_provider=provider_name)
    )
    print(user)
    if user is None:
        user = User.from_details(
            auth_infos=[AuthenticationInfo.from_details(auth_user_id=userinfo['email'], auth_provider=provider_name)],
            user_type='human',
            permissions=get_default_permissions()
        )
    return user


def is_user_admin():
  user = JsonObject.make_from_dict(session.get('user', None))
  logging.debug(session.get('user', None))
  logging.debug(session)
  logging.debug(user)
  if user is None or not user.check_permission(service="users", action="admin"):
    return False
  else:
    return True


@api.route('/current_user')
class CurrentUserHandler(flask_restplus.Resource):
  # noinspection PyMethodMayBeStatic
  @api.doc(responses={
    200: 'Success.',
    401: 'Unknown - you need to be logged in.',
  })
  def get(self):
    """ Get current user details.

    PS: Login with <a href="v1/oauth_login/google" target="new">google oauth in a new tab</a>.
    """
    session_user = JsonObject.make_from_dict(session.get('user', None))
    if session_user is None:
      return {"message": "No user found, not authorized!"}, 401
    else:
      return [session_user.to_json_map()], 200


@api.route('/users')
class UserListHandler(flask_restplus.Resource):
  # noinspection PyMethodMayBeStatic
  @api.doc(responses={
    200: 'Success.',
    401: 'Unauthorized - you need to be an admin. Use <a href="../auth/v1/oauth_login/google" target="new">google oauth</a> to login and/ or request access at https://github.com/vedavaapi/vedavaapi_py_api .',
  })
  def get(self):
    """Just list the users.

    PS: Login with <a href="v1/oauth_login/google" target="new">google oauth in a new tab</a>.
    """
    if not is_user_admin():
      return {"message": "Not authorized!"}, 401
    else:
      user_list = [user for user in get_db().find(find_filter={})]
      logging.debug(user_list)
      return user_list, 200

  post_parser = api.parser()
  post_parser.add_argument('jsonStr', location='json', help="Should fit the User schema.")

  @api.expect(post_parser, validate=False)
  # TODO: The below fails silently. Await response on https://github.com/noirbizarre/flask-restplus/issues/194#issuecomment-284703984 .
  @api.expect(User.schema, validate=True)
  @api.doc(responses={
    200: 'Update success.',
    401: 'Unauthorized - you need to be an admin. Use <a href="../auth/v1/oauth_login/google" target="new">google oauth</a> to login and request access at https://github.com/vedavaapi/vedavaapi_py_api .',
    417: 'JSON schema validation error.',
    409: 'Object with matching info already exists. Please edit that instead or delete it.',
  })
  def post(self):
    """Add a new user, identified by the authentication_infos array.

    PS: Login with <a href="v1/oauth_login/google" target="new">google oauth in a new tab</a>.
    """
    logging.info(str(request.json))
    if not is_user_admin():
      return {"message": "User is not an admin!"}, 401

    user = common_data_containers.JsonObject.make_from_dict(request.json)
    if not isinstance(user, User):
      return {"message": "Input JSON object does not conform to User.schema: " + User.schema}, 417

    # Check to see if there are other entries in the database with identical authentication info.
    matching_users = get_db().get_matching_users_by_auth_infos(user=user)
    if len(matching_users) > 0:
      logging.warning(str(matching_users[0]))
      return {"message": "Object with matching info already exists. Please edit that instead or delete it.",
              "matching_user": matching_users[0].to_json_map()
              }, 409

    try:
      user.update_collection(db_interface=get_db())
    except ValidationError as e:
      import traceback
      message = {
        "message": "Some input object does not fit the schema.",
        "exception_dump": (traceback.format_exc())
      }
      return message, 417
    return user.to_json_map(), 200

@api.route('/users/<string:id>')
@api.param('id', 'Hint: Get one from the JSON object returned by another GET call. ')
class UserHandler(flask_restplus.Resource):
  # noinspection PyMethodMayBeStatic,PyProtectedMember,PyProtectedMember,PyShadowingBuiltins
  @api.doc(responses={
    200: 'Success.',
    401: 'Unauthorized - you need to be an admin, or you need to be accessing your own data. Use <a href="../auth/v1/oauth_login/google" target="new">google oauth</a> to login and request access at https://github.com/vedavaapi/vedavaapi_py_api .',
    404: 'id not found'
  })
  def get(self, id):
    """Just get the user info.

    PS: Login with <a href="v1/oauth_login/google" target="new">google oauth in a new tab</a>.
    :param id: String
    :return: A User object.
    """
    matching_user = get_db().find_by_id(id=id)

    if matching_user is None:
      return {"message": "User not found!"}, 404

    session_user = JsonObject.make_from_dict(session.get('user', None))

    if not is_user_admin() and (session_user is None or session_user._id != matching_user._id):
      return {"message": "User is not an admin!"}, 401

    return matching_user, 200

  post_parser = api.parser()
  post_parser.add_argument('jsonStr', location='json')

  # noinspection PyProtectedMember,PyProtectedMember,PyShadowingBuiltins
  @api.expect(post_parser, validate=False)
  # TODO: The below fails silently. Await response on https://github.com/noirbizarre/flask-restplus/issues/194#issuecomment-284703984 .
  @api.expect(User.schema, validate=True)
  @api.doc(responses={
    200: 'Update success.',
    401: 'Unauthorized - you need to be an admin, or you need to be accessing your own data. Use <a href="../auth/v1/oauth_login/google" target="new">google oauth</a> to login and request access at https://github.com/vedavaapi/vedavaapi_py_api .',
    404: 'id not found',
    417: 'JSON schema validation error.',
    409: 'A different object with matching info already exists. Please edit that instead or delete it.',
  })
  def post(self, id):
    """Modify a user.

    PS: Login with <a href="v1/oauth_login/google" target="new">google oauth in a new tab</a>.
    """
    matching_user = get_db().find_by_id(id=id)

    if matching_user is None:
      return {"message": "User not found!"}, 404

    session_user = JsonObject.make_from_dict(session.get('user', None))

    logging.info(str(request.json))
    if not is_user_admin() and (session_user is None or session_user._id != matching_user._id):
      return {"message": "Unauthorized!"}, 401

    user = common_data_containers.JsonObject.make_from_dict(request.json)
    if not isinstance(user, User):
      return {"message": "Input JSON object does not conform to User.schema: " + User.schema}, 417

    # Check to see if there are other entries in the database with identical authentication info.
    matching_users = get_db().get_matching_users_by_auth_infos(user=user)
    if len(matching_users) > 1:
      logging.warning(str(matching_users))
      return {"message": "Another object with matching info already exists. Please delete it first.",
              "another_matching_user": str(matching_users)
              }, 409

    try:
      user.update_collection(db_interface=get_db())
    except ValidationError as e:
      import traceback
      message = {
        "message": "Some input object does not fit the schema.",
        "exception_dump": (traceback.format_exc())
      }
      return message, 417
    return user.to_json_map(), 200

  delete_parser = api.parser()

  # noinspection PyProtectedMember,PyProtectedMember,PyShadowingBuiltins
  @api.expect(delete_parser, validate=False)
  # TODO: The below fails silently. Await response on https://github.com/noirbizarre/flask-restplus/issues/194#issuecomment-284703984 .
  @api.expect(User.schema, validate=True)
  @api.doc(responses={
    200: 'Update success.',
    401: 'Unauthorized - you need to be an admin, or you need to be accessing your own data. Use <a href="../auth/v1/oauth_login/google" target="new">google oauth</a> to login and request access at https://github.com/vedavaapi/vedavaapi_py_api .',
    404: 'id not found',
  })
  def delete(self, id):
    """Delete a user.

    PS: Login with <a href="v1/oauth_login/google" target="new">google oauth in a new tab</a>.
    """
    matching_user = get_db().find_by_id(id=id)

    if matching_user is None:
      return {"message": "User not found!"}, 404

    session_user = JsonObject.make_from_dict(session.get('user', None))

    logging.info(str(request.json))
    if not is_user_admin() and (session_user is None or session_user._id != matching_user._id):
      return {"message": "Unauthorized!"}, 401
    matching_user.delete_in_collection(db_interface=get_db())
    return {}, 200

@api.route('/password_login')
class PasswordLogin(flask_restplus.Resource):
  post_parser = api.parser()
  post_parser.add_argument('user_id', type=str, location='form')
  post_parser.add_argument('user_secret', type=str, location='form')
  post_parser.add_argument('next_url', type=str, location='form')

  @api.expect(post_parser, validate=True)
  @api.doc(responses={
    200: 'Login success.',
    401: 'Unauthorized.',
  })
  def post(self):
    """ Log in with a password.

    Passwords are convenient for authenticating bots.
    For human debugging - just use Google oauth login as an admin (but ensure that url is localhost, not a bare ip address).
    """
    logging.info('(raw) request.get_data(): ' + request.get_data().decode(encoding='utf-8'))
    logging.info('request.form: ' + str(request.form))
    logging.info('request.values: ' + str(request.values))
    user_id = request.form.get('user_id')
    user_secret = request.form.get('user_secret')
    user = get_db().get_user_from_auth_info(auth_info=AuthenticationInfo.from_details(auth_user_id=user_id,
                                                                                      auth_provider="vedavaapi"))
    logging.debug(user)
    if user is None:
      return {"message": "No such user_id"}, 401
    else:
      authentication_matches = list(
        filter(lambda info: info.auth_provider == "vedavaapi" and info.check_password(user_secret),
               user.authentication_infos))
      if not authentication_matches or len(authentication_matches) == 0:
        return {"message": "Bad pw"}, 401
      session['user'] = user.to_json_map()
    # logging.debug(request.args)
    # Example request.args: {'code': '4/BukA679ASNPe5xvrbq_2aJXD_OKxjQ5BpCnAsCqX_Io', 'state': 'http://localhost:63342/vedavaapi/ullekhanam-ui/docs/v0/html/viewbook.html?_id=59adf4eed63f84441023762d'}
    next_url = request.form.get('next_url')
    if next_url is not None:
      # Not using redirect(next_url) because:
      #   Attempting to redirect to file:///home/vvasuki/ullekhanam-ui/docs/v0/html/viewbook.html?_id=59adf4eed63f84441023762d failed with "unsafe redirect."
      return Response(redirect_js(next_url))
      # return redirect(next_url)
    else:
      return {"message": "Did not get a next_url, it seems!"}, 200


@api.route("/logout")
class LogoutHandler(flask_restplus.Resource):
  get_parser = api.parser()
  get_parser.add_argument('next_url', type=str, location='args')

  @api.expect(get_parser, validate=True)
  def get(self):
    session.pop('oauth_token', None)
    session.pop('user', None)
    next_url = request.args.get('next_url')
    if next_url is not None:
      return Response(redirect_js(next_url))
    else:
      return {"message": "Did not get a next_url, it seems!"}, 200


# noinspection PyMethodMayBeStatic
@api.route('/schemas')
class SchemaListHandler(flask_restplus.Resource):
  def get(self):
    """Just list the schemas."""
    from sanskrit_data.schema import common, users
    logging.debug(common.get_schemas(common))
    schemas = common.get_schemas(common)
    schemas.update(common.get_schemas(users))
    return schemas, 200

