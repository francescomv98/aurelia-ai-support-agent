from src.agent.state import AgentState
from src.logging.logger import logger

def authorize_action(state: AgentState) -> AgentState:
    """
    Verify that the authenticated user is allowed to execute
    the approved action.

    The actual write tool performs the final authorization check
    against the target resource.
    """
    pending_action = state["pending_action"]

    if pending_action is None:
        logger.error("Authorization requested without pending action")
        raise ValueError("No pending action available for authorization.")
    
    approval_result = state["tool_result"]

    if approval_result != "The requested action was approved.":
        logger.warning("Write action was not approved", action_type=pending_action.action_type)
        return state

    logger.info("Write action authorized", action_type=pending_action.action_type, user_id=state["authenticated_user"].user_id)

    return state