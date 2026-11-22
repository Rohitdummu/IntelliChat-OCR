import logging

from app.core.database import SessionLocal
from app.models.document import Document

from app.services.blob_storage import generate_read_sas_url
from app.services.document_classifier import DocumentClassifier
from app.services.document_extractor import DocumentExtractionService
from app.services.extraction_normalizer import ExtractionNormalizer
from app.core.field_metadata_merger import FieldMetadataMerger

logger = logging.getLogger(__name__)


async def process_document_task_new(document_id: str):

    db = SessionLocal()

    try:
        # Step 1: Fetch document
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:
            logger.warning("Document not found: %s", document_id)
            return

        # Step 2: Update status
        document.status = "processing"
        document.error_message = None
        db.commit()

        logger.info("Starting document processing: %s", document_id)

        # Step 3: Generate Blob SAS URL
        sas_url = generate_read_sas_url(document.blob_name)

        # Step 4: Classify document
        classifier = DocumentClassifier()

        classification = await classifier.classify_document(sas_url)

        document_type = classification["document_type"]

        # Step 5: Handle multiple documents
        if document_type == "multiple_documents":

            document.status = "needs_review"
            document.error_message = (
                "Multiple document categories detected in one PDF"
            )

            db.commit()

            logger.warning(
                "Manual review required: %s",
                document_id
            )
            return

        # Normalize known classifier category aliases
        # category_aliases = {
        #     "laboratory_report": "lab_report",
        #     "insurance_claim_form": "claim_form",
        # }

        # document_type = category_aliases.get(
        #     document_type,
        #     document_type
        # )

        # Step 6: Save classification
        document.document_type = document_type
        document.status = "classified"
        db.commit()

        logger.info(
            "Document classified: %s -> %s",
            document_id,
            document_type
        )

        # Step 7: Extract document fields
        extractor = DocumentExtractionService()

        extraction_result = await extractor.extract_document(
            document_type=document_type,
            sas_url=sas_url
        )


        # Step 8: Normalize extracted fields
        normalizer = ExtractionNormalizer()

        structured_result = normalizer.normalize(
            response=extraction_result,
            document_type=document_type
        )

        logger.info(
            "Document normalization completed: %s",
            document_id
        )

        # Step 9: Merge field metadata
        enriched_fields = FieldMetadataMerger.merge(
            fields=structured_result.get("fields", {}),
            field_metadata=structured_result.get("field_metadata", {})
        )

        # Preserve document-level information
        enriched_result = {
            **structured_result,
            "fields": enriched_fields
        }

        logger.info(
            "Field metadata merging completed: %s",
            document_id
        )

        # Step 10: Save both results in PostgreSQL

        # Original Azure response (unchanged)
        document.analysis_result = extraction_result

        # Enriched structured JSON
        document.structured_result = enriched_result

        document.status = "completed"
        document.error_message = None

        # Mark corrected document version ready for review
        if document.previous_document_id:
            document.review_status = "pending_review"

        db.commit()

        logger.info(
            "Document extraction, normalization and metadata merging completed: %s",
            document_id
        )
        
    except Exception as e:

        db.rollback()

        logger.exception(
            "Document processing failed: %s",
            document_id
        )

        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if document:
            document.status = "failed"
            document.error_message = str(e)
            db.commit()

    finally:
        db.close()