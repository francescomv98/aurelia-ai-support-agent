from unittest.mock import MagicMock
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import select
from src.agent.graph import build_agent_graph
from src.auth.models import AuthenticatedUser, UserRole
from src.database.models import SupportTicket
from src.database.session import SessionLocal

def create_test_graph():
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "tool"

    action_response = MagicMock()
    action_response.ticket_number = "TCK-5021"
    action_response.status = None
    action_response.priority = "P1"
    action_response.subject = None
    action_response.description = None

    chat_model.with_structured_output.return_value.invoke.side_effect = [ route_response, action_response ]

    response = MagicMock()
    response.content = "Support ticket TCK-5021 was updated successfully."

    chat_model.invoke.return_value = response

    rag_service = MagicMock()
    rag_service.retrieve_context.return_value = []

    db = SessionLocal()

    checkpointer = InMemorySaver()

    agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

    return agent_graph, db


def create_initial_state():
    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    return {
        "user_query": (
            "Update support ticket TCK-5021 and change the priority to P1."
        ),
        "authenticated_user": user,
        "route": "tool",
        "retrieved_context": [],
        "tool_type": None,
        "pending_action": None,
        "tool_result": "",
        "response": ""
    }


@pytest.mark.integration
def test_update_support_ticket_through_agent_workflow() -> None:
    agent_graph, db = create_test_graph()

    try:
        ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == "TCK-5021", SupportTicket.customer_id == 1))

        assert ticket is not None

        config = { "configurable": { "thread_id": "integration-update-support-ticket-test" }}

        result = agent_graph.invoke(create_initial_state(), config=config)

        assert "__interrupt__" in result

        interrupt_data = result["__interrupt__"][0].value

        assert interrupt_data["type"] == "human_approval"
        assert interrupt_data["action_type"] == "update_support_ticket"

        assert interrupt_data["parameters"]["ticket_number"] == "TCK-5021"
        assert interrupt_data["parameters"]["status"] is None
        assert interrupt_data["parameters"]["priority"] == "P1"
        assert interrupt_data["parameters"]["subject"] is None
        assert interrupt_data["parameters"]["description"] is None

        resumed_result = agent_graph.invoke(Command(resume="APPROVED"), config=config)

        assert resumed_result["response"] == "Support ticket TCK-5021 was updated successfully."

        db.refresh(ticket)

        assert ticket.priority == "P1"
        assert ticket.ticket_number == "TCK-5021"

    finally:
        db.close()


@pytest.mark.integration
def test_update_support_ticket_rejected_by_human() -> None:
    agent_graph, db = create_test_graph()

    try:
        ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == "TCK-5021", SupportTicket.customer_id == 1))

        assert ticket is not None

        original_priority = ticket.priority

        config = { "configurable": { "thread_id": "integration-update-support-ticket-rejected-test" }}

        result = agent_graph.invoke(create_initial_state(), config=config)

        assert "__interrupt__" in result

        resumed_result = agent_graph.invoke(Command(resume="REJECTED"), config=config)

        assert resumed_result["response"] is not None

        db.refresh(ticket)

        assert ticket.priority == original_priority

    finally:
        db.close()