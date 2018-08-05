import sys
import os

from vedavaapi.common import VedavaapiService

class VedavaapiStore(VedavaapiService):
    def __init__(self, name, conf):
        super(VedavaapiStore, self).__init__(name, conf)

        self.client = None
        if self.config["db_type"] == "couchdb":
            from sanskrit_data.db.implementations import couchdb
            self.client = couchdb.CloudantApiClient(url=self.config["couchdb_host"])
        elif self.config["db_type"] == "mongo":
            from sanskrit_data.db.implementations import mongodb
            self.client = mongodb.Client(url=self.config["mongo_host"])
        
api_blueprints = []
