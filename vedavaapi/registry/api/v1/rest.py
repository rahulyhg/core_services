
import flask_restplus
from flask import g
from jsonschema import ValidationError
from sanskrit_ld.schema.services import VedavaapiService

from vedavaapi.objectdb.helpers import ObjModelException, projection_helper, objstore_helper
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
    delete_parser.add_argument('resource_ids', location='form', required=True)

    @api.expect(get_parser, validate=True)
    @require_oauth(token_required=False)
    def get(self):
        args = self.get_parser.parse_args()

        filter_doc = jsonify_argument(args.get('filter_doc', None), key='filter_doc') or {}
        check_argument_type(filter_doc, (dict, ), key='filter_doc')

        projection = jsonify_argument(args.get('projection', None), key='projection') or {"permissions": 0}
        try:
            projection_helper.validate_projection(projection)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        selector_doc = filter_doc.copy()
        selector_doc.update({"jsonClass": VedavaapiService.json_class})
        try:
            service_jsons = objstore_helper.get_read_permitted_resource_jsons(
                g.registry_colln, current_token.user_id, current_token.group_ids, selector_doc)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        services_map = {}
        for service_json in service_jsons:
            service_name = service_json['service_name']
            if service_name not in services_map:
                services_map[service_name] = []

            projected_service_json = projection_helper.project_doc(service_json, projection)
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

        return_projection = jsonify_argument(
            args.get('return_projection', None), key='return_projection') or {"permissions": 0}
        try:
            projection_helper.validate_projection(return_projection)
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)

        try:
            service_id = objstore_helper.create_or_update(
                g.registry_colln, service_json, current_token.user_id, current_token.group_ids,
                initial_agents=get_initial_agents(), non_updatable_attributes=['service_name'])
        except ObjModelException as e:
            return error_response(message=e.message, code=e.http_response_code)
        except ValidationError as e:
            return error_response(message='schema validation error', code=400, details={"error": str(e)})

        updated_service_json = g.registry_colln.find_one({"_id": service_id}, projection=return_projection)
        return updated_service_json

    @api.expect(delete_parser, validate=True)
    @require_oauth()
    def delete(self):
        args = self.delete_parser.parse_args()

        resource_ids = jsonify_argument(args['resource_ids'])
        check_argument_type(resource_ids, (list,))

        ids_validity = False not in [isinstance(_id, str) for _id in resource_ids]
        if not ids_validity:
            return error_response(message='ids should be strings', code=404)

        delete_report = []

        for resource_id in resource_ids:
            deleted, deleted_res_ids = objstore_helper.delete_tree(
                g.registry_colln, resource_id, current_token.user_id, current_token.group_ids)

            delete_report.append({
                "deleted": deleted,
                "deleted_resource_ids": deleted_res_ids
            })

        return delete_report
