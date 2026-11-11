from src.agent.state import AgentState, PendingAction
from src.app_logging.logger import logger
from src.services.exceptions import LLMError, ValidationError
import openai
from pydantic import BaseModel, Field
import re
from typing import Literal

# Keep in sync with TicketCategory / TicketPriority / TicketStatus in src/database/models.py.
TicketCategoryValue = Literal["TECHNICAL", "MAINTENANCE", "ORDER", "SHIPPING", "WARRANTY", "BILLING", "GENERAL"]
TicketPriorityValue = Literal["P1", "P2", "P3", "P4"]
TicketStatusValue = Literal["OPEN", "IN_PROGRESS", "WAITING_CUSTOMER", "RESOLVED", "CLOSED"]

class OrderItem(BaseModel):
    product_code: str = Field(description="The product code requested by the customer, such as AIS-100, AIS-200 or AIS-500.")
    quantity: int = Field(description="The quantity of the product requested by the customer.", gt=0)


class CreateOrderAction(BaseModel):
    items: list[OrderItem] = Field(description="The products and quantities that should be included in the new order.")


class CancelOrderAction(BaseModel):
    order_number: str = Field(description="The order number to cancel, such as ORD-10245.")


class CreateSupportTicketAction(BaseModel):
    category: TicketCategoryValue = Field(description="The support ticket category.")
    priority: TicketPriorityValue = Field(description="The ticket priority, from P1 (most urgent) to P4.")
    subject: str = Field(description="A concise subject describing the support issue.")
    description: str = Field(description="A clear description of the issue reported by the customer.")
    machine_serial: str | None = Field(default=None, description="The machine serial number explicitly mentioned by the customer, if applicable.")
    customer_id: int | None = Field(default=None, description="The target customer ID explicitly requested by the customer, if applicable. For example, 'customer 2' means customer ID 2.")


class UpdateSupportTicketAction(BaseModel):
    ticket_number: str = Field(description="The support ticket number to update, such as TCK-5021.")
    status: TicketStatusValue | None = Field(default=None, description="The new ticket status, if the customer wants to change it.")
    priority: TicketPriorityValue | None = Field(default=None, description="The new ticket priority, from P1 (most urgent) to P4, if the customer wants to change it.")
    subject: str | None = Field(default=None, description="The new ticket subject, if the customer wants to change it.")
    description: str | None = Field(default=None, description="The new ticket description, if the customer wants to change it.")


def _invoke_structured(chat_model, schema: type[BaseModel], prompt: str):
    """Run a structured-output extraction, mapping OpenAI failures to LLMError."""
    try:
        return chat_model.with_structured_output(schema).invoke(prompt)
    except openai.APIError as exc:
        logger.exception("LLM extraction failed", schema=schema.__name__)
        raise LLMError("The AI service request failed.") from exc


WRITE_ACTION_KEYWORDS = {
    "create_order": (
        "create order",
        "create an order",
        "place order",
        "place an order",
        "place a new order",
        "create a new order",
        "make an order",
        "i want to purchase",
        "i would like to purchase",
        "i'd like to purchase"
    ),
    "cancel_order": (
        "cancel order",
        "cancel my order",
        "cancel the order"
    ),
    "create_support_ticket": (
        "create support ticket",
        "create a support ticket",
        "open support ticket",
        "open a support ticket",
        "create a ticket",
        "open a ticket",
        "open support case",
        "open a support case",
        "create support case",
        "create a support case"
    ),
    "update_support_ticket": (
        "update support ticket",
        "update the support ticket",
        "update the ticket",
        "update ticket",
        "change support ticket",
        "change the support ticket",
        "modify support ticket",
        "modify the support ticket",
        "close support ticket",
        "close the support ticket"
    )
}


def prepare_action(state: AgentState, chat_model=None) -> AgentState:
    """
    Identify and prepare a write operation.

    The function prepares the requested action and extracts the
    parameters required by the corresponding write tool.

    It does not perform authorization or database mutations.
    """
    action_type = None

    normalized_query = re.sub(r"\bp[1-4]\b", "", state["user_query"].lower())
    normalized_query = " ".join(normalized_query.split())

    for candidate_action, keywords in WRITE_ACTION_KEYWORDS.items():
        if any(keyword in normalized_query for keyword in keywords):
            action_type = candidate_action
            break

    if action_type is None:
        logger.info("No write action detected")

        return {
            **state,
            "pending_action": None
        }

    if action_type == "create_order":
        if chat_model is None:
            raise ValueError("Chat model is required to prepare a create_order action.")

        action = _invoke_structured(chat_model, CreateOrderAction,
            f"""
Extract the order information from the following customer request.

Customer request:
{state["user_query"]}

Return the products and quantities explicitly requested by the customer.
Do not invent products or quantities.
"""
        )

        pending_action = PendingAction(
            action_type="create_order",
            description=state["user_query"].strip(),
            parameters={
                "items": [
                    {
                        "product_code": item.product_code,
                        "quantity": item.quantity,
                    }
                    for item in action.items
                ]
            }
        )

        logger.info("Write action prepared", action_type="create_order", item_count=len(action.items))

        return {
            **state,
            "pending_action": pending_action
        }

    if action_type == "cancel_order":
        if chat_model is None:
            raise ValueError("Chat model is required to prepare a cancel_order action.")

        action = _invoke_structured(chat_model, CancelOrderAction,
            f"""
    Extract the order number from the following customer request.

    Customer request:
    {state["user_query"]}

    Return the order number explicitly mentioned by the customer.
    Do not invent an order number.
    """
        )

        pending_action = PendingAction(
            action_type="cancel_order",
            description=state["user_query"].strip(),
            parameters={
                "order_number": action.order_number
            }
        )

        logger.info("Write action prepared", action_type="cancel_order", order_number=action.order_number)

        return {
            **state,
            "pending_action": pending_action
        }

    if action_type == "create_support_ticket":
        if chat_model is None:
            raise ValueError("Chat model is required to prepare a create_support_ticket action.")

        action = _invoke_structured(chat_model, CreateSupportTicketAction,
            f"""
    Extract the support ticket information from the following customer request.

    Customer request:
    {state["user_query"]}

    Return:
    - the ticket category
    - the ticket priority
    - a concise subject
    - a clear description of the issue
    - the machine serial number if explicitly mentioned
    - the target customer ID if explicitly requested

    For the target customer ID:
    - If the customer explicitly mentions a customer number, extract its numeric ID.
    - For example, "customer 2" means customer ID 2.
    - If no target customer is explicitly mentioned, return null.

    Do not invent information that is not present in the customer request.
    """
        )

        pending_action = PendingAction(
            action_type="create_support_ticket",
            description=state["user_query"].strip(),
            parameters={
                "category": action.category,
                "priority": action.priority,
                "subject": action.subject,
                "description": action.description,
                "machine_serial": action.machine_serial,
                "customer_id": action.customer_id
            }
        )

        logger.info("Write action prepared", action_type="create_support_ticket", priority=action.priority, machine_serial=action.machine_serial)

        return {
            **state,
            "pending_action": pending_action
        }

    if action_type == "update_support_ticket":
        if chat_model is None:
            raise ValueError("Chat model is required to prepare an update_support_ticket action.")

        action = _invoke_structured(chat_model, UpdateSupportTicketAction,
            f"""
Extract the support ticket update information from the following customer request.

Customer request:
{state["user_query"]}

Return:
- the support ticket number
- the new status, if explicitly requested
- the new priority, if explicitly requested
- the new subject, if explicitly requested
- the new description, if explicitly requested

Only return values explicitly requested by the customer.
Do not invent or modify values that are not mentioned.
"""
        )

        if all(value is None for value in (action.status, action.priority, action.subject, action.description)):
            raise ValidationError("At least one support ticket field must be provided for update.")

        pending_action = PendingAction(
            action_type="update_support_ticket",
            description=state["user_query"].strip(),
            parameters={
                "ticket_number": action.ticket_number,
                "status": action.status,
                "priority": action.priority,
                "subject": action.subject,
                "description": action.description
            }
        )

        logger.info("Write action prepared", action_type="update_support_ticket", ticket_number=action.ticket_number)

        return {
            **state,
            "pending_action": pending_action
        }

    raise ValueError(f"Unsupported write action: {action_type}")
