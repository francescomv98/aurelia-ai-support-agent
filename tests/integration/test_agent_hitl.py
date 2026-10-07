from unittest.mock import MagicMock
from langgraph.types import Command
from src.agent.graph import build_agent_graph
from src.auth.models import AuthenticatedUser, UserRole
from langgraph.checkpoint.memory import InMemorySaver
import pytest

def create_test_graph():
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "tool"

    action_response = MagicMock()

    action_item = MagicMock()
    action_item.product_code = "AIS-200"
    action_item.quantity = 2

    action_response.items = [action_item]

    chat_model.with_structured_output.return_value.invoke.side_effect = [ route_response, action_response]

    response = MagicMock()
    response.content = "The order action was approved."

    chat_model.invoke.return_value = response

    rag_service = MagicMock()
    rag_service.retrieve_context.return_value = []

    db = MagicMock()

    checkpointer = InMemorySaver()

    agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

    return agent_graph


def create_initial_state():
    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    return {
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


@pytest.mark.integration
@pytest.mark.anyio
async def test_agent_graph_resumes_after_human_approval():
    agent_graph = create_test_graph()

    config = {"configurable": {"thread_id": "hitl-approved-test"}}

    result = await agent_graph.ainvoke(create_initial_state(), config=config)

    assert "__interrupt__" in result

    interrupt_data = result["__interrupt__"][0].value

    assert interrupt_data["type"] == "human_approval"
    assert interrupt_data["action_type"] == "create_order"

    resumed_result = await agent_graph.ainvoke(Command(resume="APPROVED"), config=config)

    assert resumed_result["response"] == "The order action was approved."


@pytest.mark.integration
@pytest.mark.anyio
async def test_agent_graph_resumes_after_human_rejection():
    agent_graph = create_test_graph()

    config = {"configurable": {"thread_id": "hitl-rejected-test"}}

    result = await agent_graph.ainvoke(create_initial_state(), config=config)

    assert "__interrupt__" in result

    resumed_result = await agent_graph.ainvoke(Command(resume="REJECTED"), config=config)

    assert resumed_result["tool_result"] == "The requested action was rejected."