from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.agent.checkpointer import create_async_checkpointer

@pytest.mark.asyncio
async def test_create_async_checkpointer():
    mock_pool = MagicMock()
    mock_pool.open = AsyncMock()

    mock_checkpointer = MagicMock()
    mock_checkpointer.setup = AsyncMock()

    database_url = ("postgresql+psycopg://aurelia:aurelia_dev_password@localhost:5432/aurelia")

    with patch.dict("os.environ", {"DATABASE_URL": database_url}):
        with patch("src.agent.checkpointer.AsyncConnectionPool", return_value=mock_pool) as mock_pool_class:
            with patch("src.agent.checkpointer.AsyncPostgresSaver", return_value=mock_checkpointer) as mock_saver_class:
                checkpointer, pool = await create_async_checkpointer()

    assert checkpointer is mock_checkpointer
    assert pool is mock_pool

    mock_pool_class.assert_called_once()
    mock_pool.open.assert_awaited_once()
    mock_saver_class.assert_called_once_with(mock_pool)
    mock_checkpointer.setup.assert_awaited_once()
