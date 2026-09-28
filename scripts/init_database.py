from src.database.base import Base
from src.database.models import (Customer, MaintenanceRecord, Machine, Order, OrderItem, Product, Role, Shipment, SupportTicket, User)
from src.database.session import engine

def init_database() -> None:
    """Create all database tables."""

    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    print("Database tables created successfully.")


if __name__ == "__main__":
    init_database()