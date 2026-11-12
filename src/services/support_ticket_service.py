from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from enum import Enum
from src.database.models import Machine, SupportTicket, TicketCategory, TicketPriority, TicketStatus
from src.app_logging.logger import logger
from src.services.exceptions import ValidationError, DatabaseError

TICKET_NUMBER_ATTEMPTS = 3

class CreateSupportTicketResult(BaseModel):
    """Result returned when creating a support ticket."""

    status: Literal["CREATED", "FAILED"]
    ticket_number: str | None
    message: str
    

class UpdateSupportTicketResult(BaseModel):
    """Result returned when updating a support ticket."""

    status: Literal["UPDATED", "NOT_FOUND"]
    ticket_number: str | None
    message: str


def _normalize_enum(value: str, enum_type: type[Enum], field_name: str) -> str:
    """Normalize a free-text value (e.g. from the LLM) and ensure it is a valid enum member."""
    normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
    allowed = {member.value for member in enum_type}

    if normalized not in allowed:
        raise ValidationError(f"Invalid ticket {field_name} '{value}'. Allowed values: {', '.join(sorted(allowed))}.")

    return normalized


def create_support_ticket(db: Session, customer_id: int, category: str, priority: str, subject: str, description: str, machine_id: int | None = None) -> CreateSupportTicketResult:
    """Create a support ticket for a customer."""

    if not category.strip():
        raise ValidationError("Ticket category is required.")

    if not priority.strip():
        raise ValidationError("Ticket priority is required.")

    if not subject.strip():
        raise ValidationError("Ticket subject is required.")

    if not description.strip():
        raise ValidationError("Ticket description is required.")

    category = _normalize_enum(category, TicketCategory, "category")
    priority = _normalize_enum(priority, TicketPriority, "priority")

    try:
        if machine_id is not None:
            machine = db.scalar(select(Machine).where(Machine.id == machine_id, Machine.customer_id == customer_id))

            if machine is None:
                return CreateSupportTicketResult(
                    status="FAILED",
                    ticket_number=None,
                    message="The specified machine was not found for the customer."
                )

        # Ticket numbers are derived from the current maximum, so concurrent
        # requests can collide on the unique constraint; retry with a fresh number.
        for attempt in range(1, TICKET_NUMBER_ATTEMPTS + 1):
            existing_ticket_numbers = db.scalars(select(SupportTicket.ticket_number)).all()

            ticket_numbers = [
                int(ticket_number.removeprefix("TCK-"))
                for ticket_number in existing_ticket_numbers
                if ticket_number.startswith("TCK-") and ticket_number.removeprefix("TCK-").isdigit()
            ]

            next_ticket_number = max(ticket_numbers, default=5043) + 1
            ticket_number = f"TCK-{next_ticket_number}"

            ticket = SupportTicket(
                ticket_number=ticket_number,
                category=category,
                priority=priority,
                status="OPEN",
                subject=subject.strip(),
                description=description.strip(),
                created_at=datetime.now(timezone.utc),
                customer_id=customer_id,
                machine_id=machine_id
            )

            try:
                db.add(ticket)
                db.commit()
                break

            except IntegrityError:
                db.rollback()

                if attempt == TICKET_NUMBER_ATTEMPTS:
                    raise

                logger.warning("Ticket number collision, retrying", ticket_number=ticket_number, attempt=attempt)

        logger.info("Support ticket created", ticket_number=ticket_number, customer_id=customer_id, category=category, priority=priority)

        return CreateSupportTicketResult(
            status="CREATED",
            ticket_number=ticket_number,
            message=f"Support ticket {ticket_number} was created successfully."
        )

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  
    except Exception:
        db.rollback()
        logger.exception("Failed to create support ticket", customer_id=customer_id)
        raise


def update_support_ticket(db: Session, ticket_number: str, customer_id: int, status: str | None = None, priority: str | None = None, subject: str | None = None, description: str | None = None) -> UpdateSupportTicketResult:
    """Update an existing support ticket for an authorized customer."""

    if all(value is None for value in (status, priority, subject, description)):
        raise ValidationError("At least one ticket field must be provided for update.")

    if subject is not None and not subject.strip():
        raise ValidationError("Ticket subject cannot be empty.")

    if description is not None and not description.strip():
        raise ValidationError("Ticket description cannot be empty.")

    if status is not None:
        status = _normalize_enum(status, TicketStatus, "status")

    if priority is not None:
        priority = _normalize_enum(priority, TicketPriority, "priority")

    try:
        ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == ticket_number, SupportTicket.customer_id == customer_id))

        if ticket is None:
            logger.info("Support ticket not found for customer", ticket_number=ticket_number, customer_id=customer_id)

            return UpdateSupportTicketResult(
                status="NOT_FOUND",
                ticket_number=None,
                message="Support ticket not found."
            )

        if status is not None:
            ticket.status = status

        if priority is not None:
            ticket.priority = priority

        if subject is not None:
            ticket.subject = subject.strip()

        if description is not None:
            ticket.description = description.strip()

        db.commit()

        logger.info("Support ticket updated", ticket_number=ticket_number, customer_id=customer_id)

        return UpdateSupportTicketResult(
            status="UPDATED",
            ticket_number=ticket.ticket_number,
            message=f"Support ticket {ticket.ticket_number} was updated successfully."
        )

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  
    except Exception:
        db.rollback()
        logger.exception("Failed to update support ticket", ticket_number=ticket_number, customer_id=customer_id)
        raise


def get_machine_by_serial(db: Session, machine_serial: str, customer_id: int) -> Machine | None:
    """Find a machine by serial number for an authorized customer."""
    try:
        machine = db.scalar(select(Machine).where(Machine.serial_number == machine_serial, Machine.customer_id == customer_id))
    except SQLAlchemyError as exc:
        logger.exception("Database operation failed")
        raise DatabaseError("Database operation failed.") from exc  
     
    return machine