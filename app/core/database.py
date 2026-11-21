import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL = settings.DATABASE_URL

connect_args = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def init_db():
    """Verify database connectivity and required tables."""

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

            inspector = inspect(connection)
            existing_tables = inspector.get_table_names()

        required_tables = ["claims", "documents"]

        missing_tables = [
            table for table in required_tables
            if table not in existing_tables
        ]

        if missing_tables:
            raise RuntimeError(
                f"Missing database tables: {missing_tables}. "
                "Run 'alembic upgrade head' to apply migrations."
            )

        logger.info("Database connection successful")
        logger.info("Required database tables verified successfully")

    except SQLAlchemyError:
        logger.exception("Database initialization or health check failed")
        raise


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()