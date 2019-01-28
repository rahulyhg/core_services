from .. import VedavaapiAuthorizer


def myservice():
    return VedavaapiAuthorizer.instance  # type: VedavaapiAuthorizer


from .v1 import api_blueprint_v1 as api_blueprint_v1

blueprints_path_map = {
    api_blueprint_v1: "/v1",
}
