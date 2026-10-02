from unittest.mock import patch
import pytest
from src.agent.human_approval import request_human_approval
from src.agent.state import PendingAction

def test_request_human_approval_returns_approved():
    action = PendingAction(
        action_type="cancel_order",
        description="Cancel order ORD-10245",
        parameters={"order_id": "ORD-10245"}
    )

    with patch("src.agent.human_approval.interrupt", return_value="APPROVED") as mock_interrupt:
        result = request_human_approval(action)

    assert result == "APPROVED"

    mock_interrupt.assert_called_once_with(
        {
            "type": "human_approval",
            "action_type": "cancel_order",
            "description": "Cancel order ORD-10245",
            "parameters": {"order_id": "ORD-10245"}
        }
    )


def test_request_human_approval_returns_rejected():
    action = PendingAction(
        action_type="create_order",
        description="Create order for 2 units of AIS-200",
        parameters={
            "items": [
                {
                    "product_code": "PROD-200",
                    "quantity": 2
                }
            ]
        }
    )

    with patch("src.agent.human_approval.interrupt", return_value="REJECTED"):
        result = request_human_approval(action)

    assert result == "REJECTED"


def test_request_human_approval_rejects_invalid_decision():
    action = PendingAction(
        action_type="update_support_ticket",
        description="Update ticket TCK-5021",
        parameters={"status": "CLOSED"}
    )

    with patch("src.agent.human_approval.interrupt", return_value="MAYBE"):
        with pytest.raises(ValueError, match="Human approval decision must be APPROVED or REJECTED"):
            request_human_approval(action)