import pytest
from unittest.mock import MagicMock
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import select
from src.agent.graph import build_agent_graph
from src.auth.models import AuthenticatedUser, UserRole
from src.database.models import Machine, SupportTicket
from src.database.session import SessionLocal

@pytest.mark.integration
@pytest.mark.anyio
async def test_create_support_ticket_through_agent_workflow() -> None:
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "tool"

    action_response = MagicMock()
    action_response.category = "TECHNICAL"
    action_response.priority = "P2"
    action_response.subject = "Cooling temperature too high"
    action_response.description = "The cooling system temperature is above the expected threshold."
    action_response.machine_serial = "AIS2-2025-00142"

    chat_model.with_structured_output.return_value.invoke.side_effect = [ route_response, action_response ]

    response = MagicMock()
    response.content = "Support ticket created successfully."

    chat_model.invoke.return_value = response

    rag_service = MagicMock()
    rag_service.retrieve_context.return_value = []

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with SessionLocal() as db:
        machine = db.scalar(select(Machine).where(Machine.serial_number == "AIS2-2025-00142", Machine.customer_id == 1))

        assert machine is not None

        checkpointer = InMemorySaver()

        agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        initial_state = {
            "user_query": (
                "Create a P2 support ticket for machine "
                "AIS2-2025-00142 because the cooling temperature "
                "is too high."
            ),
            "authenticated_user": user,
            "route": "tool",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        config = { "configurable": { "thread_id": "integration-create-support-ticket-test" }}

        result = await agent_graph.ainvoke(initial_state, config=config)

        assert "__interrupt__" in result

        interrupt_data = result["__interrupt__"][0].value

        assert interrupt_data["type"] == "human_approval"
        assert interrupt_data["action_type"] == "create_support_ticket"

        assert interrupt_data["parameters"]["category"] == "TECHNICAL"
        assert interrupt_data["parameters"]["priority"] == "P2"
        assert interrupt_data["parameters"]["machine_serial"] == "AIS2-2025-00142"

        resumed_result = await agent_graph.ainvoke(Command(resume="APPROVED"), config=config)

        assert resumed_result["response"] == "Support ticket created successfully."

        ticket = db.scalar(select(SupportTicket).where(SupportTicket.customer_id == 1).order_by(SupportTicket.id.desc()))

        assert ticket is not None
        assert ticket.customer_id == 1
        assert ticket.machine_id == machine.id
        assert ticket.category == "TECHNICAL"
        assert ticket.priority == "P2"
        assert ticket.status == "OPEN"
        assert ticket.subject == "Cooling temperature too high"
        assert ticket.description == "The cooling system temperature is above the expected threshold."


@pytest.mark.integration
@pytest.mark.anyio
async def test_create_support_ticket_rejected_by_human() -> None:
    chat_model = MagicMock()

    route_response = MagicMock()
    route_response.route = "tool"

    action_response = MagicMock()
    action_response.category = "TECHNICAL"
    action_response.priority = "P2"
    action_response.subject = "Cooling temperature too high"
    action_response.description = "The cooling system temperature is above the expected threshold."
    action_response.machine_serial = "AIS2-2025-00142"

    chat_model.with_structured_output.return_value.invoke.side_effect = [ route_response, action_response]

    response = MagicMock()
    response.content = "The support ticket request was rejected."

    chat_model.invoke.return_value = response

    rag_service = MagicMock()
    rag_service.retrieve_context.return_value = []

    user = AuthenticatedUser(user_id=1, customer_id=1, role=UserRole.CUSTOMER)

    with SessionLocal() as db:
        machine = db.scalar(select(Machine).where(Machine.serial_number == "AIS2-2025-00142", Machine.customer_id == 1))

        assert machine is not None

        existing_ticket_ids = {ticket.id for ticket in db.scalars(select(SupportTicket).where(SupportTicket.customer_id == 1)).all()}

        checkpointer = InMemorySaver()

        agent_graph = build_agent_graph(chat_model=chat_model, rag_service=rag_service, db=db, checkpointer=checkpointer)

        initial_state = {
            "user_query": (
                "Create a P2 support ticket for machine "
                "AIS2-2025-00142 because the cooling temperature "
                "is too high."
            ),
            "authenticated_user": user,
            "route": "tool",
            "retrieved_context": [],
            "rag_available": True,
            "tool_type": None,
            "pending_action": None,
            "tool_result": "",
            "response": ""
        }

        config = { "configurable": { "thread_id": "integration-create-support-ticket-rejected-test" }}

        result = await agent_graph.ainvoke(initial_state, config=config)

        assert "__interrupt__" in result

        interrupt_data = result["__interrupt__"][0].value

        assert interrupt_data["type"] == "human_approval"
        assert interrupt_data["action_type"] == "create_support_ticket"

        resumed_result = await agent_graph.ainvoke(Command(resume="REJECTED"), config=config)

        assert resumed_result["response"] == "The support ticket request was rejected."

        created_ticket_ids = {ticket.id for ticket in db.scalars(select(SupportTicket).where(SupportTicket.customer_id == 1)).all()}

        assert created_ticket_ids == existing_ticket_ids