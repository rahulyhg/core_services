import flask
from flask import session
from .. import myservice


def get_db():
    repo_id = session.get('repo_id', myservice().vvstore.default_repo)
    if repo_id is None:
        response = flask.make_response(
            flask.jsonify({'error': 'repo not setted!'}),
            404
        )
        flask.abort(response)
    elif repo_id not in myservice().vvstore.all_repos():
        response = flask.make_response(
            flask.jsonify({'error': 'invalid repo! resetting it'}),
            404
        )
        del session['repo_id']
        flask.abort(response)
    return myservice().get_db(repo_id)


from .v0 import api_blueprint as apiv0_blueprint
from .v1 import api_blueprint as apiv1_blueprint
