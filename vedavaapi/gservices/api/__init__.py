import json

# from vedavaapi.common.api_common import get_repo

from .. import VedavaapiGservices

'''
any common little functionality that can be used in all versions should be here, and nothing else.
'''


def myservice():
    return VedavaapiGservices.instance


def get_repo():
    # instead of api_common's get_repo, we use this here, so that repo check will not be enforced unnecessarily.
    import flask
    repo_name = flask.session.get('repo_name', myservice().registry.lookup('store').default_repo)
    return repo_name


def creds_dict():
    credentials_dict = json.load(open(myservice().creds_path(get_repo())))
    return credentials_dict


from .v1 import api_blueprint_v1
