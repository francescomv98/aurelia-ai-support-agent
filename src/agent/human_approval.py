from typing import Literal
from langgraph.types import interrupt
from src.agent.state import PendingAction
from src.app_logging.logger import logger

def request_human_approval(pending_action: PendingAction) -> Literal["APPROVED", "REJECTED"]:
    """
    Pause the agent workflow until the requesting customer confirms
    or rejects a write operation.

    This is a user confirmation step, not a separate approval by a second
    person: the same customer who asked for the action resumes the thread
    (see /chat/resume, which only accepts the thread owner).
    """
    logger.info("Human approval requested", action_type=pending_action.action_type, description=pending_action.description)

    decision = interrupt(
        {
            "type": "human_approval",
            "action_type": pending_action.action_type,
            "description": pending_action.description,
            "parameters": pending_action.parameters
        }
    )

    if decision not in {"APPROVED", "REJECTED"}:
        logger.warning("Invalid human approval decision", decision=decision)
        raise ValueError("Human approval decision must be APPROVED or REJECTED.")

    logger.info("Human approval decision received", action_type=pending_action.action_type, decision=decision)

    return decision