import flask_restplus, flask


URL_PREFIX = '/v1'
api_blueprint = flask.Blueprint(name='auth1', import_name=__name__)

api = flask_restplus.Api(app=api_blueprint, version='1.0', title='vedavaapi py users API',
                         description='For detailed intro and to report issues: see <a href="https://github.com/vedavaapi/vedavaapi_py_api">here</a>. '
                                     'For a list of JSON schema-s this API uses (referred to by name in docs) see <a href="v1/schemas"> here</a>. <BR>'
                                     'Please also see the <a href="http://sanskrit-data.readthedocs.io/en/latest/sanskrit_data_schema.html#class-diagram" > class diagram </a> as well as the sources ( <a href="http://sanskrit-data.readthedocs.io/en/latest/_modules/sanskrit_data/schema/books.html#BookPortion">example</a> ) - It might help you understand the schema more easily.<BR>'
                                     'A list of REST and non-REST API routes avalilable on this server: <a href="../sitemap">sitemap</a>.',
                         default_label=api_blueprint.name, prefix=URL_PREFIX)

from ..v1 import rest
