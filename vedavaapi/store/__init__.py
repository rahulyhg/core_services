import sys
import os

from vedavaapi.common import VedavaapiService

ServiceObj = None

class VedavaapiStore(VedavaapiService):
    config_template = {
        "db_type": "mongo",
        "mongo_host": "mongodb://localhost/",
        "couchdb_host": "http://sanskrit-coders:sktcouch@localhost:5984/",
        "repositories": [
            {
                "repo_id": "ullekhanam",
                "db": "vedavaapi_ullekhanam_db",
                "db_type": "mongo",
                "file_store": "/opt/vedavaapi/data/books/ullekhanam"
            },
            {
                "repo_id": "ullekhanam_test",
                "db": "vedavaapi_ullekhanam_test_db",
                "db_type": "mongo",
                "file_store": "/opt/vedavaapi/data/books/ullekhanam_test"
            }
        ]
    }
    def __init__(self, registry, name, conf):
        super(VedavaapiStore, self).__init__(registry, name, conf)
        global ServiceObj
        ServiceObj = self

        self.client = None
        if self.config["db_type"] == "couchdb":
            from sanskrit_data.db.implementations import couchdb
            self.client = couchdb.CloudantApiClient(url=self.config["couchdb_host"])
        elif self.config["db_type"] == "mongo":
            from sanskrit_data.db.implementations import mongodb
            self.client = mongodb.Client(url=self.config["mongo_host"])

def myservice():
    return ServiceObj
        
api_blueprints = []
