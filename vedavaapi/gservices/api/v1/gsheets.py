import requests
from flask import request
from flask_restplus import Resource, Namespace, reqparse

from ..v1 import gservices, creds_dict

factory = gservices.ServiceObj.services()
gsheets = factory.gsheets()

gsheets_ns = Namespace('gsheets', description='proxy methods to gsheets')

@gsheets_ns.route('/raw/<path:path>')
class Raw(Resource):

    def get(self, path):
        qparams = request.args
        params = {}
        for key in qparams:
            values = qparams.getlist(key)
            params[key] = values[0] if len(values)==1 else values
        
        access_token_request_data = {
            'grant_type' : 'refresh_token',
            'refresh_token' : creds_dict()['refresh_token'],
            'client_id' : creds_dict()['client_id'],
            'client_secret' : creds_dict()['client_secret']
        }

        atr = requests.post(creds_dict()['token_uri'], data=access_token_request_data)
        access_token = atr.json().get('access_token', creds_dict()['token'])
        print(access_token)

        sheets_api_uri_prefix = 'https://sheets.googleapis.com/v4/spreadsheets/'
        sheets_request_url = sheets_api_uri_prefix + path
        auth_headers = {'Authorization' : atr.json().get('token_type') + ' '+ access_token}
        api_response = requests.get(sheets_request_url, params=params, headers=auth_headers)

        response_json = api_response.json()
        response_code = api_response.status_code

        if 'error' in response_json:
            return error_response(inherited_error_table=response_json)

        return response_json, response_code


@gsheets_ns.route('/<spreadsheetId>')
class Spreadsheet(Resource):
    reqparser = reqparse.RequestParser()
    reqparser.add_argument('includeSheetHeaderDetails', location='args', type=int, choices=[0, 1], default=1, help='whether to include sheet header details in response or not. give integer 1 or 0')

    def get(self, spreadsheetId):
        response_table, code = gsheets.spreadsheet_details_for(spreadsheetId, pargs=self.reqparser.parse_args())
        return response_table, code


@gsheets_ns.route('/<spreadsheetId>/<sheetId>')
class Sheet(Resource):
    reqparser = reqparse.RequestParser()

    reqparser.add_argument(
        'idType',
        location='args',
        default='gid',
        choices=['gid', 'title'],
        help='identifier type, should be "title" or "gid". default is "gid".'
    )
    reqparser.add_argument('fields', location='args', action='append', help='required fields in requested sheet. accepts multiple argument assignments seperated by ampresend in url querystring. by default all fields will be returned')

    reqparser.add_argument(
        'valuesFormat',
        location='args',
        default='maps',
        choices=['maps', 'rows', 'columns'],
        help='format in which values should be presented. should be one among "rows", "columns", "maps". by default returns as array of "maps".'
    )

    reqparser.add_argument('range', location='args', help='range of rows in required sheet')

    def get(self, spreadsheetId, sheetId):
        response_table, code = gsheets.sheet_values_for(spreadsheetId, sheetId, pargs=self.reqparser.parse_args())

        return response_table, code



def error_response(**kwargs):
    #print ('in error_response')
    response = {'error' : {}}
    is_error_inherited = 'inherited_error_table' in kwargs
    response_code = kwargs.get('code', kwargs['inherited_error_table']['error'].get('code', 500) if is_error_inherited else 500)
    response_message = kwargs.get('message', None)

    response['error']['code'] = response_code
    if response_message is not None :
        response['error']['message'] = response_message
    if is_error_inherited :
        response['error']['inherited_error'] = kwargs['inherited_error_table']['error']

    return (response), response_code
