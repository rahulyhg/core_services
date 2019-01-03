import requests
from flask import request
from flask_restplus import Resource, Namespace, reqparse

from vedavaapi.common.api_common import error_response, get_current_org

from .. import creds_dict, myservice


def gdrive():
    org_name = get_current_org()
    factory = myservice().services(org_name)
    return factory.gdrive()


gdrive_ns = Namespace('gdrive', description='proxy methods to gdrive')


@gdrive_ns.route('/raw/<path:path>')
class Raw(Resource):

    def get(self, path):
        qparams = request.args
        params = {}
        for key in qparams:
            values = qparams.getlist(key)
            params[key] = values[0] if len(values) == 1 else values

        access_token_request_data = {
            'grant_type': 'refresh_token',
            'refresh_token': creds_dict()['refresh_token'],
            'client_id': creds_dict()['client_id'],
            'client_secret': creds_dict()['client_secret']
        }

        atr = requests.post(creds_dict()['token_uri'], data=access_token_request_data)
        access_token = atr.json().get('access_token', creds_dict()['token'])
        print(access_token)

        drive_api_uri_prefix = 'https://www.googleapis.com/drive/v3/'
        drive_request_url = drive_api_uri_prefix + path
        auth_headers = {'Authorization': atr.json().get('token_type') + ' ' + access_token}
        api_response = requests.get(drive_request_url, params=params, headers=auth_headers)

        response_json = api_response.json()
        response_code = api_response.status_code

        if 'error' in response_json:
            return error_response(inherited_error_table=response_json)

        return response_json, response_code


@gdrive_ns.route('/folder/<folderId>')
class Folder(Resource):
    reqparser = reqparse.RequestParser()
    reqparser.add_argument(
        "orderBy",
        location='args', default='name_natural',
        help='A comma-separated list of sort keys. how spreadsheets should be ordered. valid options are "createdTime", "modifiedTime", "name", "name_natural", "recency", "starred". Each key sorts ascending by default, but may be reversed with the "desc" modifier. Example usage: ?orderBy=modifiedTime desc,name. default is by "name_natural".'
    )
    reqparser.add_argument(
        'mimeType',
        location='args', default=None,
        action='append',
        help='required mimetypes. if nthing passes, all mimeTypes will be considered'
    )

    def get(self, folderId):
        additional_args = self.reqparser.parse_args()
        response_table, code = gdrive().list_of_files_in_folder(folder_id=folderId, mime_types=additional_args.pop('mimeType'), additional_pargs=additional_args)

        return response_table, code
