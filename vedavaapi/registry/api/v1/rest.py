
import flask_restplus
from flask import g
from sanskrit_ld.schema.services import VedavaapiService

from vedavaapi.objectdb import objstore_helper
from vedavaapi.common.api_common import jsonify_argument, check_argument_type, error_response, get_initial_agents
from vedavaapi.common.token_helper import require_oauth, current_token

from . import api


@api.route('/services')
class Services(flask_restplus.Resource):

    get_parser = api.parser()
    get_parser.add_argument('filter_doc', location='args', default='{}')
    get_parser.add_argument('projection', location='args', default='{"permissions": 0}')

    post_parser = api.parser()
    post_parser.add_argument('service_json', location='form', required=True)
    post_parser.add_argument('return_projection', location='form')

    delete_parser = api.parser()
    delete_parser.add_argument('filter_doc', location='form', required=True)

    @api.expect(get_parser, validate=True)
    @require_oauth(token_required=False)
    def get(self):
        args = self.get_parser.parse_args()

        filter_doc = jsonify_argument(args.get('filter_doc', None), key='filter_doc') or {}
        check_argument_type(filter_doc, (dict, ), key='filter_doc')

        projection = jsonify_argument(args.get('projection', None), key='projection') or {"permissions": 0}
        try:
            objstore_helper.validate_projection(projection)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        selector_doc = filter_doc.copy()
        selector_doc.update({"jsonClass": VedavaapiService.json_class})
        try:
            service_jsons = objstore_helper.get_read_permitted_resource_jsons(
                g.registry_colln, current_token.user_id, current_token.group_ids, selector_doc)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        services_map = {}
        for service_json in service_jsons:
            service_name = service_json['service_name']
            if service_name not in services_map:
                services_map[service_name] = []

            projected_service_json = objstore_helper.project_doc(service_json, projection)
            services_map[service_name].append(projected_service_json)

        return services_map

    @api.expect(post_parser, validate=True)
    @require_oauth()
    def post(self):
        args = self.post_parser.parse_args()

        service_json = jsonify_argument(args['service_json'], key='service_json')
        check_argument_type(service_json, (dict, ))
        if service_json.get('jsonClass', None) != VedavaapiService.json_class:
            return error_response(message='invalid jsonClass', code=400)

        if 'source' not in service_json:
            service_json['source'] = g.registry_resource_id
        if service_json['source'] != g.registry_resource_id:
            return error_response(message='invalid service', code=403)
        service_obj = VedavaapiService.make_from_dict(service_json)

        return_projection = jsonify_argument(
            args.get('return_projection', None), key='return_projection') or {"permissions": 0}
        try:
            objstore_helper.validate_projection(return_projection)
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        try:
            service_id = objstore_helper.create_or_update(
                g.registry_colln, service_obj, current_token.user_id, current_token.group_ids,
                initial_agents=get_initial_agents(), non_updatable_attributes=['service_name'])
        except objstore_helper.ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        updated_service_json = g.registry_colln.find_one({"_id": service_id}, projection=return_projection)
        return updated_service_json

    @api.expect(delete_parser, validate=True)
    @require_oauth()
    def delete(self):
        args = self.delete_parser.parse_args()

        filter_doc = jsonify_argument(args['filter_doc'], key='filter_doc')
        check_argument_type(filter_doc, (dict, ), key='filter_doc')

        selector_doc = filter_doc.copy()
        selector_doc.update({"jsonClass": VedavaapiService.json_class})

        pass