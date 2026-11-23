import logging
from unittest.mock import AsyncMock, Mock

from pydantic import MongoDsn

from nsls2api.infrastructure import mongodb_setup
from nsls2api.infrastructure.mongodb_setup import create_connection_string


def test_create_connection_string():
    mongo_dsn = create_connection_string(
        host="testhost",
        port=27017,
        db_name="pytest",
        username="testuser",
        password="testpassword",
    )
    assert mongo_dsn == MongoDsn.build(
        scheme="mongodb",
        host="testhost",
        port=27017,
        path="pytest",
        username="testuser",
        password="testpassword",
    )


async def test_init_connection_does_not_log_dsn(monkeypatch, caplog):
    mongo_dsn = create_connection_string(
        host="testhost",
        port=27017,
        db_name="pytest",
        username="testuser",
        password="testpassword",
    )
    database = Mock(name="pytest")
    client = Mock()
    client.get_default_database.return_value = database
    monkeypatch.setattr(mongodb_setup, "AsyncMongoClient", Mock(return_value=client))
    monkeypatch.setattr(mongodb_setup.beanie, "init_beanie", AsyncMock())

    with caplog.at_level(logging.INFO, logger="uvicorn.error.nsls2api"):
        await mongodb_setup.init_connection(mongo_dsn)

    assert str(mongo_dsn) not in caplog.text
