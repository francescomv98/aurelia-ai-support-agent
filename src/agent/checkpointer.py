import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg_pool import ConnectionPool

load_dotenv()


def create_checkpointer() -> PostgresSaver:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    checkpointer_url = database_url.replace("postgresql+psycopg://", "postgres://")

    connection_pool = ConnectionPool(conninfo=checkpointer_url, kwargs={"autocommit": True})

    checkpointer = PostgresSaver(connection_pool)
    checkpointer.setup()

    return checkpointer


async def create_async_checkpointer() -> tuple[AsyncPostgresSaver, AsyncConnection]:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    checkpointer_url = database_url.replace("postgresql+psycopg://", "postgres://")

    connection = await AsyncConnection.connect(checkpointer_url, autocommit=True)

    checkpointer = AsyncPostgresSaver(connection)

    await checkpointer.setup()

    return checkpointer, connection