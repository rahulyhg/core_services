from vedavaapi.common.api_common import check_and_get_repo_name

from .. import myservice


def get_db():
    repo_name = check_and_get_repo_name()
    return myservice().db(repo_name)

from .v0 import api_blueprint as apiv0_blueprint
from .v1 import api_blueprint as apiv1_blueprint
