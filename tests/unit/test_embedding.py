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