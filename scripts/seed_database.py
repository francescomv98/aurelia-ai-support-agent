from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from src.database.models import (Customer, MaintenanceRecord, Machine, Order, OrderItem, Product, Role, Shipment, SupportTicket, User)
from src.database.session import SessionLocal

def seed_database() -> None:
    """Populate the database with demo enterprise data."""

    db: Session = SessionLocal()

    try:
        # ------------------------------------------------------------------
        # Roles
        # ------------------------------------------------------------------

        roles = {
            "CUSTOMER": Role(name="CUSTOMER"),
            "SUPPORT_AGENT": Role(name="SUPPORT_AGENT"),
            "ADMIN": Role(name="ADMIN")
        }

        db.add_all(roles.values())
        db.flush()

        # ------------------------------------------------------------------
        # Customers
        # ------------------------------------------------------------------

        customers = [
            Customer(
                customer_code="CUST-001",
                name="Alfa Manufacturing S.p.A.",
                industry="Automotive Components",
                country="Italy"
            ),
            Customer(
                customer_code="CUST-002",
                name="Beta Automation GmbH",
                industry="Industrial Automation",
                country="Germany"
            ),
            Customer(
                customer_code="CUST-003",
                name="Gamma Industries S.r.l.",
                industry="Packaging",
                country="Italy"
            ),
            Customer(
                customer_code="CUST-004",
                name="Delta Mechanics S.A.",
                industry="Mechanical Manufacturing",
                country="Spain"
            ),
            Customer(
                customer_code="CUST-005",
                name="Nova Production Ltd.",
                industry="Electronics Manufacturing",
                country="UK"
            )
        ]

        db.add_all(customers)
        db.flush()

        customer_map = {
            customer.customer_code: customer
            for customer in customers
        }

        # ------------------------------------------------------------------
        # Products
        # ------------------------------------------------------------------

        products = [
            Product(
                product_code="PROD-100",
                name="AIS-100",
                category="MACHINE",
                capacity_per_minute=40,
                maintenance_interval_hours=1500
            ),
            Product(
                product_code="PROD-200",
                name="AIS-200",
                category="MACHINE",
                capacity_per_minute=80,
                maintenance_interval_hours=2000
            ),
            Product(
                product_code="PROD-500",
                name="AIS-500",
                category="MACHINE",
                capacity_per_minute=180,
                maintenance_interval_hours=2500
            ),
            Product(
                product_code="SP-100",
                name="AIS-100 Spare Part",
                category="SPARE_PART"
            ),
            Product(
                product_code="SP-204",
                name="AIS-200 E-204 Cooling Component",
                category="SPARE_PART"
            ),
            Product(
                product_code="SP-500",
                name="AIS-500 Spare Part",
                category="SPARE_PART"
            ),
            Product(
                product_code="SP-COOL-01",
                name="Cooling System Component",
                category="SPARE_PART"
            ),
            Product(
                product_code="SP-SENSOR-02",
                name="Safety Sensor",
                category="SPARE_PART"
            )
        ]

        db.add_all(products)
        db.flush()

        product_map = {
            product.product_code: product
            for product in products
        }

        # ------------------------------------------------------------------
        # Machines
        # ------------------------------------------------------------------

        machines = [
            Machine(
                serial_number="AIS1-2024-00087",
                operating_hours=2840,
                status="OPERATIONAL",
                customer=customer_map["CUST-001"],
                product=product_map["PROD-100"]
            ),
            Machine(
                serial_number="AIS2-2025-00142",
                operating_hours=1734,
                status="OPERATIONAL",
                customer=customer_map["CUST-001"],
                product=product_map["PROD-200"]
            ),
            Machine(
                serial_number="AIS5-2025-00031",
                operating_hours=3120,
                status="MAINTENANCE",
                customer=customer_map["CUST-001"],
                product=product_map["PROD-500"]
            ),
            Machine(
                serial_number="AIS2-2025-00191",
                operating_hours=2315,
                status="OPERATIONAL",
                customer=customer_map["CUST-002"],
                product=product_map["PROD-200"]
            ),
            Machine(
                serial_number="AIS1-2024-00112",
                operating_hours=1220,
                status="OPERATIONAL",
                customer=customer_map["CUST-002"],
                product=product_map["PROD-100"]
            ),
            Machine(
                serial_number="AIS5-2025-00074",
                operating_hours=1845,
                status="OPERATIONAL",
                customer=customer_map["CUST-002"],
                product=product_map["PROD-500"]
            ),
            Machine(
                serial_number="AIS2-2026-00018",
                operating_hours=640,
                status="OPERATIONAL",
                customer=customer_map["CUST-003"],
                product=product_map["PROD-200"]
            ),
            Machine(
                serial_number="AIS1-2025-00156",
                operating_hours=1610,
                status="WARNING",
                customer=customer_map["CUST-003"],
                product=product_map["PROD-100"]
            ),
            Machine(
                serial_number="AIS5-2024-00052",
                operating_hours=5020,
                status="MAINTENANCE",
                customer=customer_map["CUST-003"],
                product=product_map["PROD-500"]
            ),
            Machine(
                serial_number="AIS2-2025-00221",
                operating_hours=1950,
                status="OPERATIONAL",
                customer=customer_map["CUST-004"],
                product=product_map["PROD-200"]
            ),
            Machine(
                serial_number="AIS1-2025-00177",
                operating_hours=930,
                status="OPERATIONAL",
                customer=customer_map["CUST-004"],
                product=product_map["PROD-100"]
            ),
            Machine(
                serial_number="AIS5-2026-00009",
                operating_hours=410,
                status="OPERATIONAL",
                customer=customer_map["CUST-005"],
                product=product_map["PROD-500"]
            )
        ]

        db.add_all(machines)
        db.flush()

        machine_map = {
            machine.serial_number: machine
            for machine in machines
        }

        # ------------------------------------------------------------------
        # Maintenance records
        # ------------------------------------------------------------------

        maintenance_records = [
            MaintenanceRecord(
                machine=machine_map["AIS2-2025-00142"],
                maintenance_type="PREVENTIVE",
                operating_hours=1000,
                performed_at=datetime(2025, 6, 10, 10, 0),
                notes="Scheduled preventive maintenance completed."
            ),
            MaintenanceRecord(
                machine=machine_map["AIS2-2025-00142"],
                maintenance_type="PREVENTIVE",
                operating_hours=1500,
                performed_at=datetime(2026, 2, 18, 9, 30),
                notes="Scheduled preventive maintenance completed."
            ),
            MaintenanceRecord(
                machine=machine_map["AIS5-2024-00052"],
                maintenance_type="PREVENTIVE",
                operating_hours=2500,
                performed_at=datetime(2025, 1, 20, 8, 30),
                notes="Preventive maintenance completed."
            ),
            MaintenanceRecord(
                machine=machine_map["AIS5-2024-00052"],
                maintenance_type="CORRECTIVE",
                operating_hours=4100,
                performed_at=datetime(2025, 11, 5, 14, 0),
                notes="Cooling system corrective intervention."
            ),
            MaintenanceRecord(
                machine=machine_map["AIS1-2025-00156"],
                maintenance_type="PREVENTIVE",
                operating_hours=1500,
                performed_at=datetime(2026, 5, 12, 11, 0),
                notes="Scheduled preventive maintenance completed."
            ),
            MaintenanceRecord(
                machine=machine_map["AIS2-2025-00191"],
                maintenance_type="PREVENTIVE",
                operating_hours=2000,
                performed_at=datetime(2026, 4, 8, 10, 0),
                notes="Scheduled preventive maintenance completed."
            )
        ]

        db.add_all(maintenance_records)

        # ------------------------------------------------------------------
        # Users
        # ------------------------------------------------------------------

        # Demo password hashes generated from the same development password.
        # Authentication implementation will be added later.
        demo_password_hash = (
            "DEMO_HASH_PLACEHOLDER"
        )

        users = [
            User(
                username="alfa.support",
                password_hash=demo_password_hash,
                role=roles["CUSTOMER"],
                customer=customer_map["CUST-001"]
            ),
            User(
                username="beta.operations",
                password_hash=demo_password_hash,
                role=roles["CUSTOMER"],
                customer=customer_map["CUST-002"]
            ),
            User(
                username="gamma.manager",
                password_hash=demo_password_hash,
                role=roles["CUSTOMER"],
                customer=customer_map["CUST-003"]
            ),
            User(
                username="delta.maintenance",
                password_hash=demo_password_hash,
                role=roles["CUSTOMER"],
                customer=customer_map["CUST-004"]
            ),
            User(
                username="nova.operator",
                password_hash=demo_password_hash,
                role=roles["CUSTOMER"],
                customer=customer_map["CUST-005"]
            ),
            User(
                username="mario.rossi",
                password_hash=demo_password_hash,
                role=roles["SUPPORT_AGENT"]
            ),
            User(
                username="lucia.bianchi",
                password_hash=demo_password_hash,
                role=roles["SUPPORT_AGENT"]
            ),
            User(
                username="admin.system",
                password_hash=demo_password_hash,
                role=roles["ADMIN"]
            )
        ]

        db.add_all(users)

        # ------------------------------------------------------------------
        # Orders
        # ------------------------------------------------------------------

        orders = [
            Order(
                order_number="ORD-10241",
                status="DELIVERED",
                order_date=datetime(2026, 7, 2, 10, 0),
                customer=customer_map["CUST-001"]
            ),
            Order(
                order_number="ORD-10242",
                status="PROCESSING",
                order_date=datetime(2026, 8, 10, 14, 30),
                customer=customer_map["CUST-002"]
            ),
            Order(
                order_number="ORD-10243",
                status="DELIVERED",
                order_date=datetime(2026, 8, 15, 9, 15),
                customer=customer_map["CUST-003"]
            ),
            Order(
                order_number="ORD-10244",
                status="CONFIRMED",
                order_date=datetime(2026, 9, 5, 11, 45),
                customer=customer_map["CUST-004"]
            ),
            Order(
                order_number="ORD-10245",
                status="SHIPPED",
                order_date=datetime(2026, 9, 15, 13, 0),
                customer=customer_map["CUST-001"]
            )
        ]

        db.add_all(orders)
        db.flush()

        order_map = {
            order.order_number: order
            for order in orders
        }

        # ------------------------------------------------------------------
        # Order items
        # ------------------------------------------------------------------

        order_items = [
            OrderItem(
                order=order_map["ORD-10241"],
                product=product_map["PROD-100"],
                quantity=1,
                unit_price=Decimal("85000.00")
            ),
            OrderItem(
                order=order_map["ORD-10242"],
                product=product_map["PROD-500"],
                quantity=1,
                unit_price=Decimal("245000.00")
            ),
            OrderItem(
                order=order_map["ORD-10243"],
                product=product_map["SP-COOL-01"],
                quantity=3,
                unit_price=Decimal("1250.00")
            ),
            OrderItem(
                order=order_map["ORD-10244"],
                product=product_map["SP-SENSOR-02"],
                quantity=8,
                unit_price=Decimal("340.00")
            ),
            OrderItem(
                order=order_map["ORD-10245"],
                product=product_map["PROD-200"],
                quantity=2,
                unit_price=Decimal("135000.00")
            ),
            OrderItem(
                order=order_map["ORD-10245"],
                product=product_map["SP-204"],
                quantity=4,
                unit_price=Decimal("1850.00")
            )
        ]

        db.add_all(order_items)

        # ------------------------------------------------------------------
        # Shipments
        # ------------------------------------------------------------------

        shipments = [
            Shipment(
                tracking_number="SHIP-90228",
                carrier="DHL",
                status="DELIVERED",
                estimated_delivery=datetime(2026, 7, 10),
                order=order_map["ORD-10241"]
            ),
            Shipment(
                tracking_number="SHIP-90229",
                carrier="DHL",
                status="IN_TRANSIT",
                estimated_delivery=datetime(2026, 8, 22),
                order=order_map["ORD-10242"]
            ),
            Shipment(
                tracking_number="SHIP-90230",
                carrier="UPS",
                status="DELIVERED",
                estimated_delivery=datetime(2026, 8, 21),
                order=order_map["ORD-10243"]
            ),
            Shipment(
                tracking_number="SHIP-90231",
                carrier="DHL",
                status="IN_TRANSIT",
                estimated_delivery=datetime(2026, 9, 30),
                order=order_map["ORD-10245"]
            )
        ]

        db.add_all(shipments)

        # ------------------------------------------------------------------
        # Support tickets
        # ------------------------------------------------------------------

        tickets = [
            SupportTicket(
                ticket_number="TCK-5021",
                category="TECHNICAL",
                priority="P2",
                status="IN_PROGRESS",
                subject="AIS-200 reports error E-204",
                description=(
                    "Machine reports cooling system temperature above "
                    "threshold during startup."
                ),
                created_at=datetime(2026, 9, 20, 8, 45),
                customer=customer_map["CUST-001"],
                machine=machine_map["AIS2-2025-00142"]
            ),
            SupportTicket(
                ticket_number="TCK-5034",
                category="MAINTENANCE",
                priority="P1",
                status="OPEN",
                subject="Production line stopped",
                description=(
                    "Production line stopped unexpectedly and requires "
                    "urgent technical assistance."
                ),
                created_at=datetime(2026, 9, 21, 7, 30),
                customer=customer_map["CUST-003"],
                machine=machine_map["AIS5-2024-00052"]
            ),
            SupportTicket(
                ticket_number="TCK-5041",
                category="SHIPPING",
                priority="P3",
                status="RESOLVED",
                subject="Shipment delayed",
                description="Customer reported a delay in shipment delivery.",
                created_at=datetime(2026, 9, 10, 15, 20),
                customer=customer_map["CUST-002"]
            ),
            SupportTicket(
                ticket_number="TCK-5042",
                category="ORDER",
                priority="P4",
                status="CLOSED",
                subject="Order confirmation request",
                description="Customer requested confirmation of a recent order.",
                created_at=datetime(2026, 9, 11, 10, 10),
                customer=customer_map["CUST-004"]
            ),
            SupportTicket(
                ticket_number="TCK-5043",
                category="WARRANTY",
                priority="P3",
                status="WAITING_CUSTOMER",
                subject="Warranty intervention request",
                description=(
                    "Customer requested information about technical "
                    "intervention under warranty."
                ),
                created_at=datetime(2026, 9, 12, 9, 0),
                customer=customer_map["CUST-005"],
                machine=machine_map["AIS5-2026-00009"]
            )
        ]

        db.add_all(tickets)

        db.commit()

        print("Database seeded successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()