import os
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.auth.password import hash_password
from src.logging.logger import configure_logging, logger
from datetime import datetime
from decimal import Decimal
from src.database.models import (Customer, MaintenanceRecord, Machine, Order, OrderItem, Product, Role, Shipment, SupportTicket, User)
from src.database.session import SessionLocal

def main() -> None:
    """Populate the database with demo enterprise data."""

    configure_logging()
    
    db: Session = SessionLocal()

    logger.info("Starting database seed")

    try:
                # ------------------------------------------------------------------
                # Roles
                # ------------------------------------------------------------------

                roles = {}

                for role_name in ("CUSTOMER", "SUPPORT_AGENT", "ADMIN"):
                    role = db.scalar(select(Role).where(Role.name == role_name))

                    if role is None:
                        role = Role(name=role_name)
                        db.add(role)

                    roles[role_name] = role

                db.flush()

                # ------------------------------------------------------------------
                # Customers
                # ------------------------------------------------------------------
        
                customer_data = [
                    {
                        "customer_code": "CUST-001",
                        "name": "Alfa Manufacturing S.p.A.",
                        "industry": "Automotive Components",
                        "country": "Italy"
                    },
                    {
                        "customer_code": "CUST-002",
                        "name": "Beta Automation GmbH",
                        "industry": "Industrial Automation",
                        "country": "Germany"
                    },
                    {
                        "customer_code": "CUST-003",
                        "name": "Gamma Industries S.r.l.",
                        "industry": "Packaging",
                        "country": "Italy"
                    },
                    {
                        "customer_code": "CUST-004",
                        "name": "Delta Mechanics S.A.",
                        "industry": "Mechanical Manufacturing",
                        "country": "Spain"
                    },
                    {
                        "customer_code": "CUST-005",
                        "name": "Nova Production Ltd.",
                        "industry": "Electronics Manufacturing",
                        "country": "UK"
                    }
                ]

                customer_map = {}

                for data in customer_data:
                    customer = db.scalar(select(Customer).where(Customer.customer_code == data["customer_code"]))

                    if customer is None:
                        customer = Customer(**data)
                        db.add(customer)
                    else:
                        customer.name = data["name"]
                        customer.industry = data["industry"]
                        customer.country = data["country"]

                    customer_map[data["customer_code"]] = customer

                db.flush()
        
                # ------------------------------------------------------------------
                # Products
                # ------------------------------------------------------------------

                product_data = [
                    {
                        "product_code": "PROD-100",
                        "name": "AIS-100",
                        "category": "MACHINE",
                        "capacity_per_minute": 40,
                        "maintenance_interval_hours": 1500
                    },
                    {
                        "product_code": "PROD-200",
                        "name": "AIS-200",
                        "category": "MACHINE",
                        "capacity_per_minute": 80,
                        "maintenance_interval_hours": 2000
                    },
                    {
                        "product_code": "PROD-500",
                        "name": "AIS-500",
                        "category": "MACHINE",
                        "capacity_per_minute": 180,
                        "maintenance_interval_hours": 2500
                    },
                    {
                        "product_code": "SP-100",
                        "name": "AIS-100 Spare Part",
                        "category": "SPARE_PART"
                    },
                    {
                        "product_code": "SP-204",
                        "name": "AIS-200 E-204 Cooling Component",
                        "category": "SPARE_PART"
                    },
                    {
                        "product_code": "SP-500",
                        "name": "AIS-500 Spare Part",
                        "category": "SPARE_PART"
                    },
                    {
                        "product_code": "SP-COOL-01",
                        "name": "Cooling System Component",
                        "category": "SPARE_PART"
                    },
                    {
                        "product_code": "SP-SENSOR-02",
                        "name": "Safety Sensor",
                        "category": "SPARE_PART"
                    }
                ]

                product_map = {}

                for data in product_data:
                    product = db.scalar(select(Product).where(Product.product_code == data["product_code"]))

                    if product is None:
                        product = Product(**data)
                        db.add(product)
                    else:
                        for field, value in data.items():
                            setattr(product, field, value)

                    product_map[data["product_code"]] = product

                db.flush()
        
                # ------------------------------------------------------------------
                # Machines
                # ------------------------------------------------------------------

                machine_data = [
                    {
                        "serial_number": "AIS1-2024-00087",
                        "operating_hours": 2840,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-001",
                        "product_code": "PROD-100"
                    },
                    {
                        "serial_number": "AIS2-2025-00142",
                        "operating_hours": 1734,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-001",
                        "product_code": "PROD-200"
                    },
                    {
                        "serial_number": "AIS5-2025-00031",
                        "operating_hours": 3120,
                        "status": "MAINTENANCE",
                        "customer_code": "CUST-001",
                        "product_code": "PROD-500"
                    },
                    {
                        "serial_number": "AIS2-2025-00191",
                        "operating_hours": 2315,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-002",
                        "product_code": "PROD-200"
                    },
                    {
                        "serial_number": "AIS1-2024-00112",
                        "operating_hours": 1220,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-002",
                        "product_code": "PROD-100"
                    },
                    {
                        "serial_number": "AIS5-2025-00074",
                        "operating_hours": 1845,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-002",
                        "product_code": "PROD-500"
                    },
                    {
                        "serial_number": "AIS2-2026-00018",
                        "operating_hours": 640,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-003",
                        "product_code": "PROD-200"
                    },
                    {
                        "serial_number": "AIS1-2025-00156",
                        "operating_hours": 1610,
                        "status": "WARNING",
                        "customer_code": "CUST-003",
                        "product_code": "PROD-100"
                    },
                    {
                        "serial_number": "AIS5-2024-00052",
                        "operating_hours": 5020,
                        "status": "MAINTENANCE",
                        "customer_code": "CUST-003",
                        "product_code": "PROD-500"
                    },
                    {
                        "serial_number": "AIS2-2025-00221",
                        "operating_hours": 1950,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-004",
                        "product_code": "PROD-200"
                    },
                    {
                        "serial_number": "AIS1-2025-00177",
                        "operating_hours": 930,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-004",
                        "product_code": "PROD-100"
                    },
                    {
                        "serial_number": "AIS5-2026-00009",
                        "operating_hours": 410,
                        "status": "OPERATIONAL",
                        "customer_code": "CUST-005",
                        "product_code": "PROD-500"
                    }
                ]

                machine_map = {}

                for data in machine_data:
                    machine = db.scalar(select(Machine).where(Machine.serial_number == data["serial_number"]))

                    customer = customer_map[data["customer_code"]]
                    product = product_map[data["product_code"]]

                    if machine is None:
                        machine = Machine(
                            serial_number=data["serial_number"],
                            operating_hours=data["operating_hours"],
                            status=data["status"],
                            customer=customer,
                            product=product
                        )
                        db.add(machine)
                    else:
                        machine.operating_hours = data["operating_hours"]
                        machine.status = data["status"]
                        machine.customer = customer
                        machine.product = product

                    machine_map[data["serial_number"]] = machine

                db.flush()
        
                # ------------------------------------------------------------------
                # Maintenance records
                # ------------------------------------------------------------------

                maintenance_data = [
                    {
                        "machine_serial_number": "AIS2-2025-00142",
                        "maintenance_type": "PREVENTIVE",
                        "operating_hours": 1000,
                        "performed_at": datetime(2025, 6, 10, 10, 0),
                        "notes": "Scheduled preventive maintenance completed."
                    },
                    {
                        "machine_serial_number": "AIS2-2025-00142",
                        "maintenance_type": "PREVENTIVE",
                        "operating_hours": 1500,
                        "performed_at": datetime(2026, 2, 18, 9, 30),
                        "notes": "Scheduled preventive maintenance completed."
                    },
                    {
                        "machine_serial_number": "AIS5-2024-00052",
                        "maintenance_type": "PREVENTIVE",
                        "operating_hours": 2500,
                        "performed_at": datetime(2025, 1, 20, 8, 30),
                        "notes": "Preventive maintenance completed."
                    },
                    {
                        "machine_serial_number": "AIS5-2024-00052",
                        "maintenance_type": "CORRECTIVE",
                        "operating_hours": 4100,
                        "performed_at": datetime(2025, 11, 5, 14, 0),
                        "notes": "Cooling system corrective intervention."
                    },
                    {
                        "machine_serial_number": "AIS1-2025-00156",
                        "maintenance_type": "PREVENTIVE",
                        "operating_hours": 1500,
                        "performed_at": datetime(2026, 5, 12, 11, 0),
                        "notes": "Scheduled preventive maintenance completed."
                    },
                    {
                        "machine_serial_number": "AIS2-2025-00191",
                        "maintenance_type": "PREVENTIVE",
                        "operating_hours": 2000,
                        "performed_at": datetime(2026, 4, 8, 10, 0),
                        "notes": "Scheduled preventive maintenance completed."
                    }
                ]

                for data in maintenance_data:
                    machine = machine_map[data["machine_serial_number"]]

                    maintenance_record = db.scalar(select(MaintenanceRecord).where(
                            MaintenanceRecord.machine_id == machine.id,
                            MaintenanceRecord.maintenance_type == data["maintenance_type"],
                            MaintenanceRecord.operating_hours == data["operating_hours"],
                            MaintenanceRecord.performed_at == data["performed_at"]
                        )
                    )

                    if maintenance_record is None:
                        maintenance_record = MaintenanceRecord(
                            machine=machine,
                            maintenance_type=data["maintenance_type"],
                            operating_hours=data["operating_hours"],
                            performed_at=data["performed_at"],
                            notes=data["notes"]
                        )
                        db.add(maintenance_record)
                    else:
                        maintenance_record.notes = data["notes"]
        
                
                # ------------------------------------------------------------------
                # Users
                # ------------------------------------------------------------------

                # Development-only password used to generate hashes for seeded users.
                # Never use this default password in production.
                demo_password = os.getenv("AURELIA_DEMO_PASSWORD", "AureliaDemo123!")
                demo_password_hash = hash_password(demo_password)

                user_data = [
                    {
                        "username": "alfa.support",
                        "role": "CUSTOMER",
                        "customer_code": "CUST-001"
                    },
                    {
                        "username": "beta.operations",
                        "role": "CUSTOMER",
                        "customer_code": "CUST-002"
                    },
                    {
                        "username": "gamma.manager",
                        "role": "CUSTOMER",
                        "customer_code": "CUST-003"
                    },
                    {
                        "username": "delta.maintenance",
                        "role": "CUSTOMER",
                        "customer_code": "CUST-004"
                    },
                    {
                        "username": "nova.operator",
                        "role": "CUSTOMER",
                        "customer_code": "CUST-005"
                    },
                    {
                        "username": "mario.rossi",
                        "role": "SUPPORT_AGENT",
                        "customer_code": None
                    },
                    {
                        "username": "lucia.bianchi",
                        "role": "SUPPORT_AGENT",
                        "customer_code": None
                    },
                    {
                        "username": "admin.system",
                        "role": "ADMIN",
                        "customer_code": None
                    }
                ]

                for data in user_data:
                    user = db.scalar(select(User).where(User.username == data["username"]))

                    role = roles[data["role"]]
                    customer_code = data["customer_code"]
                    customer = (customer_map[customer_code] if customer_code is not None else None)

                    if user is None:
                        user = User(
                            username=data["username"],
                            password_hash=demo_password_hash,
                            is_active=True,
                            role=role,
                            customer=customer
                        )
                        db.add(user)

                        logger.info("Seeded user", username=user.username, role=role.name)
                    else:
                        user.password_hash = demo_password_hash
                        user.is_active = True
                        user.role = role
                        user.customer = customer

                        logger.info("Updated seeded user", username=user.username, role=role.name)

                db.flush()
        
                # ------------------------------------------------------------------
                # Orders
                # ------------------------------------------------------------------
        
                order_data = [
                    {
                        "order_number": "ORD-10241",
                        "status": "DELIVERED",
                        "order_date": datetime(2026, 7, 2, 10, 0),
                        "customer_code": "CUST-001"
                    },
                    {
                        "order_number": "ORD-10242",
                        "status": "PROCESSING",
                        "order_date": datetime(2026, 8, 10, 14, 30),
                        "customer_code": "CUST-002"
                    },
                    {
                        "order_number": "ORD-10243",
                        "status": "DELIVERED",
                        "order_date": datetime(2026, 8, 15, 9, 15),
                        "customer_code": "CUST-003"
                    },
                    {
                        "order_number": "ORD-10244",
                        "status": "CONFIRMED",
                        "order_date": datetime(2026, 9, 5, 11, 45),
                        "customer_code": "CUST-004"
                    },
                    {
                        "order_number": "ORD-10245",
                        "status": "SHIPPED",
                        "order_date": datetime(2026, 9, 15, 13, 0),
                        "customer_code": "CUST-001"
                    }
                ]

                order_map = {}

                for data in order_data:
                    order = db.scalar(select(Order).where(Order.order_number == data["order_number"]))

                    customer = customer_map[data["customer_code"]]

                    if order is None:
                        order = Order(
                            order_number=data["order_number"],
                            status=data["status"],
                            order_date=data["order_date"],
                            customer=customer
                        )
                        db.add(order)
                    else:
                        order.status = data["status"]
                        order.order_date = data["order_date"]
                        order.customer = customer

                    order_map[data["order_number"]] = order

                db.flush()
            
                # ------------------------------------------------------------------
                # Order items
                # ------------------------------------------------------------------

                order_item_data = [
                    {
                        "order_number": "ORD-10241",
                        "product_code": "PROD-100",
                        "quantity": 1,
                        "unit_price": Decimal("85000.00")
                    },
                    {
                        "order_number": "ORD-10242",
                        "product_code": "PROD-500",
                        "quantity": 1,
                        "unit_price": Decimal("245000.00")
                    },
                    {
                        "order_number": "ORD-10243",
                        "product_code": "SP-COOL-01",
                        "quantity": 3,
                        "unit_price": Decimal("1250.00")
                    },
                    {
                        "order_number": "ORD-10244",
                        "product_code": "SP-SENSOR-02",
                        "quantity": 8,
                        "unit_price": Decimal("340.00")
                    },
                    {
                        "order_number": "ORD-10245",
                        "product_code": "PROD-200",
                        "quantity": 2,
                        "unit_price": Decimal("135000.00")
                    },
                    {
                        "order_number": "ORD-10245",
                        "product_code": "SP-204",
                        "quantity": 4,
                        "unit_price": Decimal("1850.00")
                    }
                ]

                for data in order_item_data:
                    order = order_map[data["order_number"]]
                    product = product_map[data["product_code"]]

                    order_item = db.scalar(select(OrderItem).where(
                            OrderItem.order_id == order.id,
                            OrderItem.product_id == product.id,
                            OrderItem.unit_price == data["unit_price"]
                        )
                    )

                    if order_item is None:
                        order_item = OrderItem(
                            order=order,
                            product=product,
                            quantity=data["quantity"],
                            unit_price=data["unit_price"]
                        )
                        db.add(order_item)
                    else:
                        order_item.quantity = data["quantity"]
        
                # ------------------------------------------------------------------
                # Shipments
                # ------------------------------------------------------------------

                shipment_data = [
                    {
                        "tracking_number": "SHIP-90228",
                        "carrier": "DHL",
                        "status": "DELIVERED",
                        "estimated_delivery": datetime(2026, 7, 10),
                        "order_number": "ORD-10241"
                    },
                    {
                        "tracking_number": "SHIP-90229",
                        "carrier": "DHL",
                        "status": "IN_TRANSIT",
                        "estimated_delivery": datetime(2026, 8, 22),
                        "order_number": "ORD-10242"
                    },
                    {
                        "tracking_number": "SHIP-90230",
                        "carrier": "UPS",
                        "status": "DELIVERED",
                        "estimated_delivery": datetime(2026, 8, 21),
                        "order_number": "ORD-10243"
                    },
                    {
                        "tracking_number": "SHIP-90231",
                        "carrier": "DHL",
                        "status": "IN_TRANSIT",
                        "estimated_delivery": datetime(2026, 9, 30),
                        "order_number": "ORD-10245"
                    }
                ]

                for data in shipment_data:
                    order = order_map[data["order_number"]]

                    shipment = db.scalar(select(Shipment).where(Shipment.tracking_number == data["tracking_number"]))

                    if shipment is None:
                        shipment = Shipment(
                            tracking_number=data["tracking_number"],
                            carrier=data["carrier"],
                            status=data["status"],
                            estimated_delivery=data["estimated_delivery"],
                            order=order
                        )
                        db.add(shipment)
                    else:
                        shipment.carrier = data["carrier"]
                        shipment.status = data["status"]
                        shipment.estimated_delivery = data["estimated_delivery"]
                        shipment.order = order
        
                # ------------------------------------------------------------------
                # Support tickets
                # ------------------------------------------------------------------

                ticket_data = [
                    {
                        "ticket_number": "TCK-5021",
                        "category": "TECHNICAL",
                        "priority": "P2",
                        "status": "IN_PROGRESS",
                        "subject": "AIS-200 reports error E-204",
                        "description": "Machine reports cooling system temperature above Threshold during startup.",
                        "created_at": datetime(2026, 9, 20, 8, 45),
                        "customer_code": "CUST-001",
                        "machine_serial_number": "AIS2-2025-00142",
                    },
                    {
                        "ticket_number": "TCK-5034",
                        "category": "MAINTENANCE",
                        "priority": "P1",
                        "status": "OPEN",
                        "subject": "Production line stopped",
                        "description": "Production line stopped unexpectedly and requires urgent technical assistance.",
                        "created_at": datetime(2026, 9, 21, 7, 30),
                        "customer_code": "CUST-003",
                        "machine_serial_number": "AIS5-2024-00052"
                    },
                    {
                        "ticket_number": "TCK-5041",
                        "category": "SHIPPING",
                        "priority": "P3",
                        "status": "RESOLVED",
                        "subject": "Shipment delayed",
                        "description": "Customer reported a delay in shipment delivery.",
                        "created_at": datetime(2026, 9, 10, 15, 20),
                        "customer_code": "CUST-002",
                        "machine_serial_number": None
                    },
                    {
                        "ticket_number": "TCK-5042",
                        "category": "ORDER",
                        "priority": "P4",
                        "status": "CLOSED",
                        "subject": "Order confirmation request",
                        "description": "Customer requested confirmation of a recent order.",
                        "created_at": datetime(2026, 9, 11, 10, 10),
                        "customer_code": "CUST-004",
                        "machine_serial_number": None
                    },
                    {
                        "ticket_number": "TCK-5043",
                        "category": "WARRANTY",
                        "priority": "P3",
                        "status": "WAITING_CUSTOMER",
                        "subject": "Warranty intervention request",
                        "description": "Customer requested information about technical intervention under warranty.",
                        "created_at": datetime(2026, 9, 12, 9, 0),
                        "customer_code": "CUST-005",
                        "machine_serial_number": "AIS5-2026-00009"
                    }
                ]

                for data in ticket_data:
                    customer = customer_map[data["customer_code"]]

                    machine_serial_number = data["machine_serial_number"]
                    machine = (machine_map[machine_serial_number] if machine_serial_number is not None else None)

                    ticket = db.scalar(select(SupportTicket).where(SupportTicket.ticket_number == data["ticket_number"]))

                    if ticket is None:
                        ticket = SupportTicket(
                            ticket_number=data["ticket_number"],
                            category=data["category"],
                            priority=data["priority"],
                            status=data["status"],
                            subject=data["subject"],
                            description=data["description"],
                            created_at=data["created_at"],
                            customer=customer,
                            machine=machine
                        )
                        db.add(ticket)
                    else:
                        ticket.category = data["category"]
                        ticket.priority = data["priority"]
                        ticket.status = data["status"]
                        ticket.subject = data["subject"]
                        ticket.description = data["description"]
                        ticket.created_at = data["created_at"]
                        ticket.customer = customer
                        ticket.machine = machine

                db.commit()      

                logger.info("Database seeded successfully",
                    roles_created=len(roles),
                    customers_created=len(customer_data),
                    products_created=len(product_data),
                    machines_created=len(machine_data),
                    orders_created=len(order_data),
                    tickets_created=len(ticket_data)
                )
    
    except Exception:
        logger.exception("Database seed failed")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()