from langchain_core.documents import Document

from src.agent.graph import build_agent_graph


class FakeRAGService:
    """Fake RAG service for agent graph tests."""

    def retrieve_context(self, query: str) -> list[Document]:
        return [
            Document(
                page_content=(
                    "AIS-200 maximum production speed is "
                    "80 units per minute."
                ),
                metadata={
                    "source": "AIS-200_technical_specifications.pdf",
                    "page": 3,
                    "category": "technical",
                },
            )
        ]

    def build_context(self, documents: list[Document]) -> str:
        return "\n\n".join(
            document.page_content
            for document in documents
        )


class FakeChatModel:
    """Fake chat model for agent graph tests."""

    def with_structured_output(self, schema):
        return FakeStructuredModel()

    def invoke(self, prompt: str):
        class FakeResponse:
            content = "The AIS-200 has a maximum speed of 80 units per minute."

        return FakeResponse()


class FakeStructuredModel:
    """Fake structured output model."""

    def invoke(self, prompt: str):
        class FakeDecision:
            route = "rag"

        return FakeDecision()


def test_agent_graph_retrieves_context() -> None:
    graph = build_agent_graph(
        rag_service=FakeRAGService(),
        chat_model=FakeChatModel(),
    )

    result = graph.invoke(
        {
            "user_query": "What is the maximum speed of AIS-200?",
            "route": "rag",
            "retrieved_context": "",
            "response": "",
        }
    )

    assert result["route"] == "rag"
    assert "80 units per minute" in result["retrieved_context"]


def test_agent_graph_generates_response() -> None:
    graph = build_agent_graph(
        rag_service=FakeRAGService(),
        chat_model=FakeChatModel(),
    )

    result = graph.invoke(
        {
            "user_query": "What is the maximum speed of AIS-200?",
            "route": "rag",
            "retrieved_context": "",
            "response": "",
        }
    )

    assert result["response"] == (
        "The AIS-200 has a maximum speed of 80 units per minute."
    )