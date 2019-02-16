
from .. import VedavaapiRegistry


def myservice():
    return VedavaapiRegistry.instance


from . import environ

from .v1 import api_blueprint_v1

api_blueprint_v1.before_request(environ.push_environ_to_g)

blueprints_path_map = {
    api_blueprint_v1: "/v1"
}
