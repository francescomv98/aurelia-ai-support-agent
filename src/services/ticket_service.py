from typing import Literal
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.database.models import SupportTicket
from src.app_logging.logger import logger
from src.services.exceptions import DatabaseError

class TicketResult(BaseModel):
    """Result returned by the support ticket service."""

    status: Literal["FOUND", "NOT_FOUND"]
    ticket_number: str | None = None
    category: str | None = None
    priority: str | None = None
    ticket_status: str | None = None
    subject: str | None = None
    message: str


def get_machine_ticket(db: Session, machine_serial: str, customer_id: int) -> TicketResult:
    """Retrieve the existing support ticket for a customer's machine."""

    logger.info("Retrieving support ticket", machine_serial=machine_serial)

    try:
        statement = (
            select(SupportTicket)
            .join(SupportTicket.machine)
            .where(SupportTicket.machine.has(serial_number=machine_serial), SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
        )
        
        ticket = db.scalar(statement)         

        if ticket is None:
            logger.info("No support ticket found for machine", machine_serial=machine_serial)

            return TicketResult(
                status="NOT_FOUND",
                message="No support ticket was found for this machine."
            )

        logger.info("Support ticket retrieved", ticket_number=ticket.ticket_number, machine_serial=machine_serial)

        return TicketResult(
            status="FOUND",
            ticket_number=ticket.ticket_number,
            category=str(ticket.category),
            priority=str(ticket.priority),
            ticket_status=str(ticket.status),
            subject=ticket.subject,
            message=(
                f"Support ticket {ticket.ticket_number} exists for "
                f"machine {machine_serial}. "
                f"Status: {ticket.status}. "
                f"Priority: {ticket.priority}. "
                f"Subject: {ticket.subject}."
            )
        )
    
    except SQLAlchemyError as exc:
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc 
    except Exception:
        logger.exception("Failed to retrieve support ticket", machine_serial=machine_serial)
        raise