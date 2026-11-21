
from contextlib import asynccontextmanager
from typing import AsyncIterator
import logging
import os

from fastapi import FastAPI

from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

from app.api.document_router import document_router
from app.api.claim_router import claim_router
from app.core.database import init_db
from app.core.logging import setup_logging
from app.services.azure_openai import AzureOpenAIService
from app.core.config import settings
from sqlalchemy.engine import make_url

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:

    logger.info("Starting IntelliChat OCR application...")

    pool = None

    try:
        # Step 1: Initialize database
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully.")

        # Step 2: Initialize LangGraph checkpointer
        logger.info("Initializing PostgreSQL checkpointer...")
        database_url = make_url(settings.DATABASE_URL)

        conninfo = database_url.set(
            drivername="postgresql"
        ).render_as_string(hide_password=False)

        pool = ConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=5,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0
            }
        )

        pool.open(wait=True)

        checkpointer = PostgresSaver(pool)
        checkpointer.setup()

        app.state.checkpointer = checkpointer
        app.state.connection_pool = pool

        logger.info("PostgreSQL checkpointer initialized successfully.")

        # Step 3: Initialize Azure OpenAI
        logger.info("Initializing Azure OpenAI...")

        azure_openai_service = AzureOpenAIService()
        app.state.azure_openai_service = azure_openai_service

        if azure_openai_service.check_connection():
            logger.info("Azure OpenAI: CONNECTED")
        else:
            logger.error("Azure OpenAI: CONNECTION FAILED")

        logger.info("IntelliChat OCR startup completed.")

        yield

    except Exception:
        logger.exception("Application startup or runtime lifespan failed.")
        raise

    finally:
        if pool is not None:
            pool.close()
            logger.info("PostgreSQL connection pool closed.")

        logger.info("IntelliChat OCR application shut down.")


app = FastAPI(
    title="Azure OCR Agent",
    description="AI-powered PDF document intelligence",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(document_router)
app.include_router(claim_router)


@app.get("/")
def home():
    return {"message": "Azure OCR Agent is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
