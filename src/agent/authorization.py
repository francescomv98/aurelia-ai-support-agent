from src.agent.state import AgentState
from src.auth.models import UserRole
from src.app_logging.logger import logger
from src.services.exceptions import AuthorizationError

def authorize_action(state: AgentState) -> AgentState:
    """Authorize a prepared write action before execution."""

    pending_action = state["pending_action"]

    if pending_action is None:
        logger.error("Authorization requested without pending action")
        raise ValueError("No pending action available for authorization.")

    approval_result = state["tool_result"]

    if approval_result != "The requested action was approved.":
        logger.warning("Write action was not approved", action_type=pending_action.action_type)
        return state

    user = state["authenticated_user"]

    requested_customer_id = pending_action.parameters.get("customer_id")

    if requested_customer_id is not None:
        if user.role == UserRole.CUSTOMER:
            if user.customer_id is None:
                raise AuthorizationError("Customer user has no customer context.")

            if requested_customer_id != user.customer_id:
                logger.warning("Write action denied for unauthorized customer", action_type=pending_action.action_type, user_id=user.user_id)
                raise AuthorizationError("The authenticated user is not authorized to perform this action for the requested customer.")

    logger.info("Write action authorized", action_type=pending_action.action_type, user_id=user.user_id)

    return state