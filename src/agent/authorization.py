from src.agent.state import AgentState
from src.app_logging.logger import logger
from src.security.authorization import require_customer_access

def authorize_action(state: AgentState) -> AgentState:
    """Authorize a confirmed write action before execution.

    Write actions always run for the authenticated customer, so the only check
    is that a customer_id carried by the action (if any) is the user's own.
    """

    pending_action = state["pending_action"]

    if pending_action is None:
        logger.error("Authorization requested without pending action")
        raise ValueError("No pending action available for authorization.")

    if state["tool_result"] != "The requested action was approved.":
        logger.warning("Write action was not confirmed", action_type=pending_action.action_type)
        return state

    user = state["authenticated_user"]

    requested_customer_id = pending_action.parameters.get("customer_id")

    if requested_customer_id is not None:
        require_customer_access(user, requested_customer_id)

    logger.info("Write action authorized", action_type=pending_action.action_type, user_id=user.user_id)

    return state
