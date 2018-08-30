import flask_restplus
from flask import session

from . import api
from ... import myservice

REPO_ID_KEY = 'repo_id'


def allowed_frontend_db_names(service_obj):
    service_conf = service_obj.config
    return service_conf.get('all_frontend_db_names', [])


@api.route('/repo')
class Repo(flask_restplus.Resource):
    post_parser = api.parser()
    post_parser.add_argument('repo_id', location='form')

    def get(self):
        if not REPO_ID_KEY in session:
            return {'error': 'repo not setted'}, 404

        return {'repo_id': session[REPO_ID_KEY]}, 200

    @api.expect(post_parser, validate=True)
    def post(self):
        args = self.post_parser.parse_args()
        if not args['repo_id'] in myservice().all_repos():
            return {'error': 'invalid repo id'}, 404
        session[REPO_ID_KEY] = args['repo_id']
        return {'repo_id': session[REPO_ID_KEY]}, 200

    def delete(self):
        del session[REPO_ID_KEY]
        return 'repo id deleted.', 200


@api.route('/all_repos')
class AllRepos(flask_restplus.Resource):

    def get(self):
        return {
                   'repos': myservice().all_repos()
               }, 200
