import os
from base64 import b64encode

import flask_restplus
from flask import session
from vedavaapi.common.api_common import get_user, error_response

from .. import myservice
from . import api


REPO_ID_KEY = 'repo_name'


def is_user_admin():
    user = get_user()
    if user is None or not user.check_permission(service="users", action="admin"):
        return False
    return True


def purge_old_repo_specifics():
    """
    this will purge all configurations specific to repo.
    like logged in user, etc., as they are defined for only specific repo as of now.
    this will prevent hijacking one repo from other.
    :return:
    """
    session.pop('oauth_token', None)
    session.pop('user', None)
    session.pop('reset_token', None)
    session.pop('reset_repo', None)
    session.pop(REPO_ID_KEY, None)


@api.route('/repo')
class Repo(flask_restplus.Resource):
    post_parser = api.parser()
    post_parser.add_argument('repo_name', location='form')

    def get(self):
        if REPO_ID_KEY not in session:
            return error_response(message='repo not setted', code=404)

        return {'repo_name': session[REPO_ID_KEY]}, 200

    @api.expect(post_parser, validate=True)
    def post(self):
        args = self.post_parser.parse_args()
        if not args['repo_name'] in myservice().repo_names():
            return error_response(message='invalid repo name', code=404)

        purge_old_repo_specifics()
        session[REPO_ID_KEY] = args['repo_name']
        return {'repo_name': session[REPO_ID_KEY]}, 200

    def delete(self):
        purge_old_repo_specifics()
        return 'repo info deleted.', 200


@api.route('/all_repos')
class AllRepos(flask_restplus.Resource):

    def get(self):
        return {
                'repos': myservice().repo_names()
               }, 200


@api.route('/actions/reset')
class Reset(flask_restplus.Resource):
    def get(self):
        if not is_user_admin():
            return error_response(message='user is not admin', code=403)
        if not session.get(REPO_ID_KEY, None):
            return error_response(message='repo not setted', code=403)
        reset_token = b64encode(os.urandom(24)).decode('utf-8')
        session['reset_token'] = reset_token
        session['reset_repo'] = session[REPO_ID_KEY]

        # logout user, so that can login again to confirm
        session.pop('oauth_token', None)
        session.pop('user', None)

        return {
            'reset_token': reset_token,
            'repo_id': session[REPO_ID_KEY],
            'message': 'to reset the repo, please login back again, and do post call to same url, attaching reset_token in form data'
        }, 200

    post_parser = api.parser()
    post_parser.add_argument('reset_token', location='form', required=True)
    post_parser.add_argument('services', location='form', default=None, help='comma seperated list of services to be resetted. if not provided, resets all services.')

    @api.expect(post_parser, validate=True)
    def post(self):
        old_repo = session.get(REPO_ID_KEY, None)
        if not old_repo:
            return 'repo not setted', 403
        if not is_user_admin():
            purge_old_repo_specifics()
            return error_response(message='user is not admin', code=403)
        if not session.get('reset_token', None) or not session.get('reset_repo', None):
            return error_response(message='first get reset_token from get call, and then make this api call', code=403)

        args = self.post_parser.parse_args()
        print(args, session)
        if not (session.get('reset_token', None) == args.get('reset_token', None)) or not (session.get('reset_repo') == old_repo):
            purge_old_repo_specifics()
            return error_response(message='illegal', code=403)

        purge_old_repo_specifics()
        services_to_be_resetted = args['services'].split(',') if args['services'] else None
        myservice().reset_repo(old_repo, service_names=services_to_be_resetted)

        session[REPO_ID_KEY] = old_repo
        return 'repo resetted successfully', 200
