# -*- coding: utf-8 -*-
"""
Tests for the ullekhanam API.
"""

from __future__ import absolute_import

import logging

import pytest
from sanskrit_data.schema import common

from vedavaapi_py_api import run

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


@pytest.fixture(scope='module')
def app_fixture(request):
  app = run.app.test_client()
  return app


def login(test_client):
  auth_info = common.JsonObject.make_from_dict(input_dict = {
    "auth_user_id": "vedavaapiBot",
    "auth_provider": "vedavaapi",
    "jsonClass": "AuthenticationInfo",
  })
  from vedavaapi_py_api import users
  vedavaapi_bot_user = users.users_db.get_user_from_auth_info(auth_info=auth_info)
  assert vedavaapi_bot_user is not None

  with test_client.session_transaction() as session:
    session["user"] = vedavaapi_bot_user.to_json_map()
    logging.debug(session.get('user', None))


def test_book_list(app_fixture):
  url = "ullekhanam/v1/dbs/ullekhanam_test_v2/books"
  response = app_fixture.get(url)
  book_nodes = common.JsonObject.make_from_pickledstring(pickle=response.data)
  assert book_nodes.__len__() > 0


def test_image_book_upload(app_fixture):
  login(app_fixture)
  pass