from typing import Literal
from langgraph.types import interrupt
from src.agent.state import PendingAction
from src.logging.logger import logger

def request_human_approval(pending_action: PendingAction) -> Literal["APPROVED", "REJECTED"]:
    """
    Pause the agent workflow and request human approval
    before executing a write operation.
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