import pytest
from src.rag.embedding import create_embeddings

def test_create_embeddings_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY environment variable is not set."):
        create_embeddings()


def test_create_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    embeddings = create_embeddings()

    assert embeddings.model == "text-embedding-3-small"

def test_create_embeddings_uses_openai_timeout_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "12")
    monkeypatch.setenv("OPENAI_MAX_RETRIES", "4")

    embeddings = create_embeddings()

    assert embeddings.request_timeout == 12.0
    assert embeddings.max_retries == 4


def test_create_embeddings_has_a_default_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.delenv("OPENAI_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("OPENAI_MAX_RETRIES", raising=False)

    embeddings = create_embeddings()

    # Without it the OpenAI SDK would wait up to 600 seconds.
    assert embeddings.request_timeout == 30.0
    assert embeddings.max_retries == 2
