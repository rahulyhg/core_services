from collections import OrderedDict

import flask_restplus
from vedavaapi.common.api_common import error_response, jsonify_argument, check_argument_type, get_current_user_id

from . import api
from ... import get_users_colln
from ....agents_helpers.models import User

agents_ns = api.namespace('default', path='/agents', description='agents namespace')


@agents_ns.route('')
class Agents(flask_restplus.Resource):

    white_listed_classes = ('JsonObject', 'WrapperObject', 'FileAnnotation')

    get_parser = api.parser()
    get_parser.add_argument('selector_doc', location='args', type=str, required=True)
    get_parser.add_argument('projection', location='args', type=str)
    get_parser.add_argument('start', location='args', type=int, required=True)
    get_parser.add_argument('numbers', location='args', type=int, required=True)
    get_parser.add_argument('sort_doc', location='args', type=str)

    @api.expect(get_parser, validate=True)
    def get(self):
        args = self.get_parser.parse_args()
        users_colln = get_users_colln()

        current_user_id = get_current_user_id()
        current_user = User.get_user(users_colln, _id=current_user_id, projection={"target": 1, "_id": 1})

        selector_doc = jsonify_argument(args['selector_doc'], key='selector_doc')
        check_argument_type(selector_doc, (dict,), key='selector_doc')

        projection = jsonify_argument(args['projection'], key='projection')
        check_argument_type(projection, (dict,), key='projection', allow_none=True)
        if projection is not None and 0 in projection.values() and 1 in projection.values():
            return error_response(message='invalid projection', code=400)

        sort_doc = jsonify_argument(args['sort_doc'], key='sort_doc')
        check_argument_type(sort_doc, (dict, list), key='sort_doc', allow_none=True)

        ops = OrderedDict()
        if sort_doc is not None:
            ops['sort'] = [sort_doc]
        ops['skip'] = [args['start']]
        ops['limit'] = [args['numbers']]

        try:
            resource_reprs = list(users_colln.find_and_do(
                selector_doc, ops,
                projection=projection, return_generator=True
            ))
        except (TypeError, ValueError):
            return error_response(message='arguments to operations seems invalid', code=400)
        except PermissionError:
            return error_response(message='user have no permission for this operation', code=403)
        return resource_reprs
