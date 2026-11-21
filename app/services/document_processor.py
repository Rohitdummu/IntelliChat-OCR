
from app.core.database import SessionLocal
from app.models.document import Document

from app.services.blob_storage import generate_read_sas_url
from app.services.doc_intelligence import (
    ContentUnderstandingClient
)
import logging

logger = logging.getLogger(__name__)

async def process_document_task(document_id: str):

    db = SessionLocal()
    cu_client = ContentUnderstandingClient()

    try:
        # 1. Retrieve document
        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        logger.info("Retrieved document", extra={
            "document_id": document_id
        })

        if not document:
            logger.warning("Document not found", extra={
                "document_id": document_id
            })
            return

        # 2. Update status
        document.status = "processing"
        document.error_message = None
        db.commit()

        # 3. Generate fresh SAS URL short lived for reading the blob
        sas_url = generate_read_sas_url(
            document.blob_name
        )
        

        # 4. Call Azure Content Understanding
        result = await cu_client.analyze_document(sas_url)

        # 5. Save analysis result
        document.analysis_result = result
        document.status = "completed"
        db.commit()

    except Exception as e:

        db.rollback()

        document = db.query(Document).filter(
            Document.id == document_id
        ).first()

        if document:
            document.status = "failed"
            document.error_message = str(e)
            db.commit()

    finally:
        db.close()
