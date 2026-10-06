import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from unittest.mock import MagicMock
from sqlalchemy import select
from src.agent.graph import build_agent_graph
from src.auth.models import AuthenticatedUser, UserRole
from src.database.models import Order, OrderItem
from src.database.session import SessionLocal

@pytest.mark.integration
def test_create_order_through_agent_workflow() -> None:
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "tool"

    action_response = MagicMock()
    action_item = MagicMock()
    action_item.product_code = "AIS-200"
    action_item.quantity = 2
    action_response.items = [action_item]

    chat_model.with_structured_output.return_value.invoke.side_effect = [ route_response, action_response ]

    response = MagicMock()
    response.content = "Order created successfully."

    chat_model.invoke.return_value = response

    rag_service = MagicMock()
    rag_service.retrieve_context.return_value = []

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with SessionLocal() as db:
        checkpointer = InMemorySaver()

        agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        initial_state = {
            "user_query": "Create an order for 2 AIS-200 machines.",
            "authenticated_user": user,
            "route": "tool",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        config = { "configurable": { "thread_id": "integration-create-order-test" }}

        result = agent_graph.invoke(initial_state, config=config)

        assert "__interrupt__" in result

        interrupt_data = result["__interrupt__"][0].value

        assert interrupt_data["type"] == "human_approval"
        assert interrupt_data["action_type"] == "create_order"

        resumed_result = agent_graph.invoke(Command(resume="APPROVED"), config=config)

        assert resumed_result["response"] == "Order created successfully."

        order = db.scalar(select(Order).where(Order.customer_id == 1).order_by(Order.id.desc()))

        assert order is not None
        assert order.status == "PENDING"

        order_item = db.scalar(select(OrderItem).where(OrderItem.order_id == order.id))

        assert order_item is not None
        assert order_item.quantity == 2