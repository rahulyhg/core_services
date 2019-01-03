import flask_restplus
from jsonschema import ValidationError
from sanskrit_ld.schema import JsonObject
from sanskrit_ld.schema.users import User as _User
from vedavaapi.common.api_common import error_response, jsonify_argument, check_argument_type, get_current_user_id, get_current_org

from . import api
from ... import get_users_colln, sign_out_user
from ....agents_helpers.models import User

me_ns = api.namespace('me', path='/me', description='personalization namespace')


def delete_attrs(obj, attrs):
    for attr in attrs:
        if hasattr(obj, attr):
            delattr(obj, attr)


# noinspection PyMethodMayBeStatic
@me_ns.route('')
class Me(flask_restplus.Resource):

    post_parser = me_ns.parser()
    post_parser.add_argument('update_doc', type=str, location='form', required=True)

    presentation_projection = {
        "permissions": 0,
        "hashedPassword": 0
    }

    def get(self):
        current_org_name = get_current_org()
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()

        current_user = User.get_user(users_colln, _id=current_user_id, projection=self.presentation_projection)
        if current_user is None:
            sign_out_user(current_org_name)
            return error_response(message='not authorized', code=400)
        return current_user.to_json_map(), 200

    @me_ns.expect(post_parser, validate=True)
    def post(self):
        current_user_id = get_current_user_id()
        users_colln = get_users_colln()
        args = self.post_parser.parse_args()

        update_doc = jsonify_argument(args['update_doc'], key='update_doc')
        check_argument_type(update_doc, (dict,), key='update_doc')

        diff = JsonObject.make_from_dict(update_doc)
        check_argument_type(diff, (_User, ), key='update_doc')
        delete_attrs(diff, ['_id', 'creator', 'created', 'permissions', 'hashedPassword', 'email'])
        User.swizzle(diff)

        try:
            diff.validate_schema(diff=True)
        except ValidationError:
            return error_response(message='arguments are invalid', code=400)

        modified = User.update_details(users_colln, User.get_user_selector_doc(_id=current_user_id), diff.to_json_map())

        if modified:
            user = User.get_user(users_colln, _id=current_user_id, projection=self.presentation_projection)
            return user.to_json_map(), 200
        else:
            return error_response(message='error in updating user info', code=400)

