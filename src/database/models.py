from datetime import datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database.base import Base

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPORT_AGENT = "SUPPORT_AGENT"
    ADMIN = "ADMIN"


class ProductCategory(str, Enum):
    MACHINE = "MACHINE"
    SPARE_PART = "SPARE_PART"


class MachineStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    WARNING = "WARNING"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ShipmentStatus(str, Enum):
    PENDING = "PENDING"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    DELAYED = "DELAYED"


class TicketCategory(str, Enum):
    TECHNICAL = "TECHNICAL"
    MAINTENANCE = "MAINTENANCE"
    ORDER = "ORDER"
    SHIPPING = "SHIPPING"
    WARRANTY = "WARRANTY"
    BILLING = "BILLING"
    GENERAL = "GENERAL"


class TicketPriority(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class TicketStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_CUSTOMER = "WAITING_CUSTOMER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class MaintenanceType(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    CORRECTIVE = "CORRECTIVE"


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[UserRole] = mapped_column(String(50), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="customer")
    machines: Mapped[list["Machine"]] = relationship(back_populates="customer")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="customer"
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"),
        nullable=True
    )

    role: Mapped["Role"] = relationship(back_populates="users")
    customer: Mapped["Customer | None"] = relationship(back_populates="users")


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[ProductCategory] = mapped_column(
        String(50),
        nullable=False
    )

    capacity_per_minute: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    maintenance_interval_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    machines: Mapped[list["Machine"]] = relationship(back_populates="product")
    order_items: Mapped[list["OrderItem"]] = relationship(
        back_populates="product"
    )


# ---------------------------------------------------------------------------
# Machines
# ---------------------------------------------------------------------------

class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    operating_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MachineStatus] = mapped_column(
        String(50),
        nullable=False
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="machines")
    product: Mapped["Product"] = relationship(back_populates="machines")

    maintenance_records: Mapped[list["MaintenanceRecord"]] = relationship(
        back_populates="machine"
    )

    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        back_populates="machine"
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    status: Mapped[OrderStatus] = mapped_column(
        String(50),
        nullable=False
    )

    order_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="orders")

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order"
    )

    shipment: Mapped["Shipment | None"] = relationship(
        back_populates="order",
        uselist=False
    )


# ---------------------------------------------------------------------------
# Order Items
# ---------------------------------------------------------------------------

class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False
    )

    order: Mapped["Order"] = relationship(
        back_populates="items"
    )

    product: Mapped["Product"] = relationship(
        back_populates="order_items"
    )


# ---------------------------------------------------------------------------
# Shipments
# ---------------------------------------------------------------------------

class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(primary_key=True)

    tracking_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    carrier: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    status: Mapped[ShipmentStatus] = mapped_column(
        String(50),
        nullable=False
    )

    estimated_delivery: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        unique=True,
        nullable=False
    )

    order: Mapped["Order"] = relationship(
        back_populates="shipment"
    )


# ---------------------------------------------------------------------------
# Maintenance Records
# ---------------------------------------------------------------------------

class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    maintenance_type: Mapped[MaintenanceType] = mapped_column(
        String(50),
        nullable=False
    )

    operating_hours: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    performed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    machine_id: Mapped[int] = mapped_column(
        ForeignKey("machines.id"),
        nullable=False
    )

    machine: Mapped["Machine"] = relationship(
        back_populates="maintenance_records"
    )


# ---------------------------------------------------------------------------
# Support Tickets
# ---------------------------------------------------------------------------

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True)

    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )

    category: Mapped[TicketCategory] = mapped_column(
        String(50),
        nullable=False
    )

    priority: Mapped[TicketPriority] = mapped_column(
        String(10),
        nullable=False
    )

    status: Mapped[TicketStatus] = mapped_column(
        String(50),
        nullable=False
    )

    subject: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False
    )

    machine_id: Mapped[int | None] = mapped_column(
        ForeignKey("machines.id"),
        nullable=True
    )

    customer: Mapped["Customer"] = relationship(
        back_populates="support_tickets"
    )

    machine: Mapped["Machine | None"] = relationship(
        back_populates="support_tickets"
    )