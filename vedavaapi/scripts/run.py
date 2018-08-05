import logging
import os, sys, getopt

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# Add parent directory to PYTHONPATH, so that vedavaapi_py_api module can be found.
sys.path.append(CODE_ROOT)
print(sys.path)

from vedavaapi_py_api import run
from sanskrit_data.db.implementations import mongodb

from sanskrit_data.schema.common import JsonObject

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

REPO_ROOT = os.path.join(CODE_ROOT, "textract-example-repo")


def dump_db(dest_dir=os.path.join(REPO_ROOT, "books_v2")):
  from vedavaapi_py_api.ullekhanam.backend import get_db
  db = get_db(db_name_frontend="ullekhanam_test")
  logging.debug(db.list_books())
  db.dump_books(dest_dir)


def import_db(db_name_frontend="ullekhanam_test_v2"):
  from vedavaapi_py_api.ullekhanam.backend import get_db
  db = get_db(db_name_frontend=db_name_frontend)
  db.import_all(rootdir=db.external_file_store)


def main(argv):
  def usage():
    logging.info("run.py [--action dump]...")
    exit(1)

  params = JsonObject()
  try:
    opts, args = getopt.getopt(argv, "ha:", ["action="])
    for opt, arg in opts:
      if opt == '-h':
        usage()
      elif opt in ("-a", "--action"):
        params.action = arg
  except getopt.GetoptError:
    usage()

  if params.action == "dump":
    dump_db()
  elif params.action == "import":
    import_db()


if __name__ == '__main__':
  main(sys.argv[1:])