from src.database.base import Base
from src.database.session import engine
from src.logging.logger import configure_logging, logger

def main() -> None:
    configure_logging()

    logger.info("Initializing database")

    try:
        Base.metadata.create_all(bind=engine)

        logger.info("Database initialized successfully", table_count=len(Base.metadata.tables))
    except Exception:
        logger.exception("Database initialization failed")
        raise


if __name__ == "__main__":
    main()