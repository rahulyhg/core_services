from sanskrit_ld.schema import JsonObject


def get_client_selector_doc(_id=None, client_id=None):
    if _id is not None:
        selector_doc = {"jsonClass": "OAuth2Client", "_id": _id}

    elif client_id is not None:
        selector_doc = {"jsonClass": "OAuth2Client", "client_id": client_id}

    else:
        selector_doc = None

    return selector_doc


def get_client_json(oauth_colln, _id=None, client_id=None, projection=None):
    client_selector_doc = get_client_selector_doc(_id=_id, client_id=client_id)

    if client_selector_doc is None:
        return None

    return oauth_colln.find_one(client_selector_doc, projection=projection)


def get_client(oauth_colln, _id=None, client_id=None, projection=None):
    client_selector_doc = get_client_selector_doc(_id=_id, client_id=client_id)

    if client_selector_doc is None:
        return None

    if projection is not None:
        if 0 in projection.values():
            projection.pop('jsonClass', None)
        else:
            projection.update({"jsonClass": 1})

    client_json = oauth_colln.find_one(client_selector_doc, projection=projection)
    client = JsonObject.make_from_dict(client_json)
    return client


def get_client_underscore_id(oauth_colln, client_id):
    client = get_client(oauth_colln, client_id=client_id, projection={"_id": 1})
    # noinspection PyProtectedMember
    return client._id if client else None


def client_exists(oauth_colln, _id=None, client_id=None):
    projection = {"_id": 1, "jsonClass": 1}
    client = get_client(oauth_colln, _id=_id, client_id=client_id, projection=projection)

    return client is not None


'''
functions for creating clients
'''


def insert_new_client(oauth_colln, client):
    client_id = oauth_colln.insert_one(client.to_json_map())
    return client_id
