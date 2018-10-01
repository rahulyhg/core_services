from vedavaapi.common.api_common import get_repo

from .. import VedavaapiUsers


def myservice():
    return VedavaapiUsers.instance


def get_colln():
    repo_name = get_repo()
    return myservice().colln(repo_name)


from .v1 import api_blueprint_v1 as api_blueprint__v1
