
import logging

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.claim import Claim

from app.services.blob_storage import generate_read_sas_url
from app.services.document_classifier import DocumentClassifier
from app.services.document_extractor import DocumentExtractionService
from app.services.extraction_normalizer import ExtractionNormalizer
from app.core.field_metadata_merger import FieldMetadataMerger
from uuid import uuid4

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

        # Step 2: Update processing status
        document.status = "processing"
        document.error_message = None
        db.commit()

        logger.info(
            "Starting document processing: %s",
            document_id
        )

        # Step 3: Generate Blob SAS URL
        sas_url = generate_read_sas_url(
            document.blob_name
        )

        # Step 4: Classify document
        classifier = DocumentClassifier()

        classification = await classifier.classify_document(
            sas_url
        )

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

        enriched_result = {
            **structured_result,
            "fields": enriched_fields
        }

        logger.info(
            "Field metadata merging completed: %s",
            document_id
        )

        # Step 10: Save extraction results
        document.analysis_result = extraction_result
        document.structured_result = enriched_result

        document.status = "completed"
        document.error_message = None

        # Step 11: Update resubmitted document review status
        if document.previous_document_id:

            document.review_status = "pending_review"

            # Mark previous claim validation as stale
            if document.claim_id:

                claim = (
                    db.query(Claim)
                    .filter(Claim.id == document.claim_id)
                    .first()
                )

                if claim and claim.validation_result:

                    previous_result = dict(
                        claim.validation_result
                    )

                    previous_result["is_stale"] = True

                    previous_result["stale_reason"] = (
                        "A corrected document version was processed"
                    )

                    previous_result["updated_document_id"] = (
                        document.id
                    )

                    claim.validation_result = previous_result

        # Step 12: Commit successful processing
        db.commit()

        logger.info(
            "Document extraction, normalization and metadata "
            "merging completed successfully: %s",
            document_id
        )

    except Exception as e:

        db.rollback()

        logger.exception(
            "Document processing failed: %s",
            document_id
        )

        try:
            document = (
                db.query(Document)
                .filter(Document.id == document_id)
                .first()
            )

            if document:
                document.status = "failed"
                document.error_message = str(e)
                db.commit()

        except Exception:
            db.rollback()

            logger.exception(
                "Failed to update document failure status: %s",
                document_id
            )

    finally:
        db.close()
