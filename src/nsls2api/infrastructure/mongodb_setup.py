import asyncio

import beanie
import click
import motor.motor_asyncio
from pydantic import MongoDsn

from nsls2api import models
from nsls2api.infrastructure.logging import logger


def create_connection_string(
    host: str,
    port: int,
    db_name: str,
    username: str | None = None,
    password: str | None = None,
) -> MongoDsn:
    return MongoDsn.build(
        scheme="mongodb",
        host=host,
        port=port,
        path=f"{db_name}",
        username=username,
        password=password,
    )


async def init_connection(mongodb_dsn: MongoDsn):
    logger.info(f"Attempting to connect to {click.style(str(mongodb_dsn), fg='green')}")

    client = motor.motor_asyncio.AsyncIOMotorClient(
        mongodb_dsn.unicode_string(), uuidRepresentation="standard"
    )

    # This is to make sure that the client is using the same event loop as the rest of the application
    client.get_io_loop = asyncio.get_event_loop

    await beanie.init_beanie(
        database=client.get_default_database(),
        document_models=models.all_models,
    )

    logger.info(
        f"Connected to {click.style(client.get_default_database().name, fg='green')} database."
    )
