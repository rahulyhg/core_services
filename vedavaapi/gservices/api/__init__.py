import json

from vedavaapi.common.helpers.api_helper import get_current_org

from .. import VedavaapiGservices

'''
any common little functionality that can be used in all versions should be here, and nothing else.
'''


def myservice():
    return VedavaapiGservices.instance


def creds_dict():
    credentials_dict = json.load(open(myservice().creds_path(get_current_org())))
    return credentials_dict


from .v1 import api_blueprint_v1


blueprints_path_map = {
    api_blueprint_v1: '/v1'
}
