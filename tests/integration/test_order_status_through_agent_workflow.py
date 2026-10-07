import pytest
from unittest.mock import MagicMock
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import select
from src.agent.graph import build_agent_graph
from src.auth.models import AuthenticatedUser, UserRole
from src.database.models import Order
from src.database.session import SessionLocal

def create_test_graph():
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "tool"

    action_response = MagicMock()
    action_response.order_number = "ORD-10244"

    chat_model.with_structured_output.return_value.invoke.side_effect = [route_response, action_response]

    response = MagicMock()
    response.content = "Order ORD-10244 was cancelled successfully."

    chat_model.invoke.return_value = response

    rag_service = MagicMock()
    rag_service.retrieve_context.return_value = []

    db = SessionLocal()

    checkpointer = InMemorySaver()

    agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

    return agent_graph, db


def create_initial_state():
    user = AuthenticatedUser(user_id=4, customer_id=4, role=UserRole.CUSTOMER)

    return {
        "user_query": "Cancel order ORD-10244.",
        "authenticated_user": user,
        "route": "tool",
        "retrieved_context": [],
        "rag_available": True,
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }


@pytest.mark.integration
@pytest.mark.anyio
async def test_cancel_order_through_agent_workflow() -> None:
    agent_graph, db = create_test_graph()

    try:
        config = {"configurable": {"thread_id": "integration-cancel-order-test"}}

        result = await agent_graph.ainvoke(create_initial_state(), config=config)

        assert "__interrupt__" in result

        interrupt_data = result["__interrupt__"][0].value

        assert interrupt_data["type"] == "human_approval"
        assert interrupt_data["action_type"] == "cancel_order"
        assert interrupt_data["parameters"]["order_number"] == "ORD-10244"

        resumed_result = await agent_graph.ainvoke(Command(resume="APPROVED"), config=config)

        assert resumed_result["response"] == "Order ORD-10244 was cancelled successfully."

        order = db.scalar(select(Order).where(Order.order_number == "ORD-10244"))

        assert order is not None
        assert order.status == "CANCELLED"

    finally:
        db.close()