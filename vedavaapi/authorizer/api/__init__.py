from .. import VedavaapiAuthorizer


def myservice():
    return VedavaapiAuthorizer.instance  # type: VedavaapiAuthorizer

from . import environ

from .v1 import api_blueprint_v1 as api_blueprint_v1

api_blueprint_v1.before_request(environ.push_environ_to_g)

blueprints_path_map = {
    api_blueprint_v1: "/v1",
}
