from .. import VedavaapiStore


def myservice():
    return VedavaapiStore.instance


from .v1 import api_blueprint_v1
