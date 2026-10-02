from src.agent.state import AgentState, PendingAction
from src.logging.logger import logger

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


def prepare_action(state: AgentState) -> AgentState:
    """
    Identify whether the user's request requires a write operation.

    This function only prepares the action. It does not perform any
    database mutation or authorization check.
    """
    query = state["user_query"].strip().lower()

    for action_type, keywords in WRITE_ACTION_KEYWORDS.items():
        if any(keyword in query for keyword in keywords):
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

    logger.info("No write action detected")

    return {
        **state,
        "pending_action": None
    }