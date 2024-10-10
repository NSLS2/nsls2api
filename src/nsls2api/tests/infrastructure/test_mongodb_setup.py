import pytest
from pydantic import MongoDsn

from nsls2api.infrastructure.mongodb_setup import create_connection_string

def test_create_connection_string():
    mongo_dsn = create_connection_string(host="testhost",
                                         port=27017,
                                         db_name="pytest",
                                         username="testuser",
                                         password="testpassword")
    assert mongo_dsn == MongoDsn.build(
        scheme="mongodb",
        host="testhost",
        port=27017,
        path="pytest",
        username="testuser",
        password="testpassword",
    )
