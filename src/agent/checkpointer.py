import os
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, AsyncConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv()


def create_checkpointer() -> PostgresSaver:
    """Create the synchronous PostgreSQL LangGraph checkpointer."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    checkpointer_url = database_url.replace(
        "postgresql+psycopg://",
        "postgres://"
    )

    connection_pool = ConnectionPool(
        conninfo=checkpointer_url,
        kwargs={
            "autocommit": True,
        },
    )

    checkpointer = PostgresSaver(connection_pool)
    checkpointer.setup()

    return checkpointer


async def create_async_checkpointer() -> tuple[AsyncPostgresSaver, AsyncConnectionPool]:
    """Create the asynchronous PostgreSQL LangGraph checkpointer."""

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")

    checkpointer_url = database_url.replace("postgresql+psycopg://", "postgres://")

    connection_pool = AsyncConnectionPool(
        conninfo=checkpointer_url,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row
        }
    )

    await connection_pool.open()

    checkpointer = AsyncPostgresSaver(connection_pool)

    await checkpointer.setup()

    return checkpointer, connection_pool