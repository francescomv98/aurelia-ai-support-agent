import pytest
from src.llm.openai_client import create_chat_model

def test_create_chat_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY environment variable is not set."):
        create_chat_model()


def test_create_chat_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "45")

    model = create_chat_model()

    assert model.model_name == "gpt-4o-mini"
    assert model.temperature == 0
    assert model.request_timeout == 45.0