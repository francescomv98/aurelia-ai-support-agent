from unittest.mock import MagicMock, patch
from src.agent.checkpointer import create_checkpointer

def test_create_checkpointer():
    mock_pool = MagicMock()
    mock_checkpointer = MagicMock()

    with patch.dict("os.environ", {"DATABASE_URL": ("postgresql+psycopg://aurelia:aurelia_dev_password@localhost:5432/aurelia")}):
        with patch("src.agent.checkpointer.ConnectionPool", return_value=mock_pool) as mock_pool_class:
            with patch("src.agent.checkpointer.PostgresSaver", return_value=mock_checkpointer) as mock_saver_class:
                result = create_checkpointer()

    assert result is mock_checkpointer

    mock_pool_class.assert_called_once_with(conninfo="postgres://aurelia:aurelia_dev_password@localhost:5432/aurelia", kwargs={"autocommit": True})

    mock_saver_class.assert_called_once_with(mock_pool)

    mock_checkpointer.setup.assert_called_once()