import os
from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

load_dotenv()


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
        },
        open=False,
        timeout=10
    )

    await connection_pool.open()

    checkpointer = AsyncPostgresSaver(connection_pool)
    await checkpointer.setup()

    return checkpointer, connection_pool