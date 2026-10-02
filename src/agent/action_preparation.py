from src.agent.state import AgentState, PendingAction
from src.logging.logger import logger
from pydantic import BaseModel, Field

class OrderItem(BaseModel):
    product_code: str = Field(description="The product code requested by the customer, such as AIS-100, AIS-200 or AIS-500.")
    quantity: int = Field(description="The quantity of the product requested by the customer.", gt=0)


class CreateOrderAction(BaseModel):
    items: list[OrderItem] = Field(description="The products and quantities that should be included in the new order.")


WRITE_ACTION_KEYWORDS = {
    "create_order": (
        "create order",
        "create an order",
        "place order",
        "place an order",
        "new order",
        "make an order",
        "purchase"
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
    query = state["user_query"].strip().lower()

    action_type = None
    
    for candidate_action, keywords in WRITE_ACTION_KEYWORDS.items():
        if any(keyword in query for keyword in keywords):
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

        structured_model = chat_model.with_structured_output(CreateOrderAction)

        action = structured_model.invoke(
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

    pending_action = PendingAction(
        action_type=action_type,
        description=state["user_query"].strip(),
        parameters={}
    )

    logger.info("Write action prepared", action_type=action_type)

    return {
        **state,
        "pending_action": pending_action
    }