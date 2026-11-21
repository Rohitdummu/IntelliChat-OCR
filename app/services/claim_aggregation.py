
import logging

from sqlalchemy.orm import Session

from app.models.document import Document

logger = logging.getLogger(__name__)


class ClaimAggregationService:

    REQUIRED_DOCUMENTS = {
        "insurance_claim_form",
        "hospital_bill",
        "discharge_summary",
        "laboratory_report",
    }

    def __init__(self, db: Session):
        self.db = db

    def aggregate_claim_documents(self, claim_id: str) -> dict:
        """
        Fetch and aggregate all documents belonging to a claim.
        """

        logger.info(
            "Starting claim document aggregation: %s",
            claim_id
        )

        # Step 1: Fetch all claim documents
        documents = (
            self.db.query(Document)
            .filter(Document.claim_id == claim_id)
            .all()
        )


        if not documents:
            logger.warning(
                "No documents found for claim: %s",
                claim_id
            )

            return {
                "claim_id": claim_id,
                "status": "documents_pending",
                "message": "No documents uploaded for this claim",
                "documents": {},
                "missing_documents": sorted(self.REQUIRED_DOCUMENTS),
                "pending_documents": [],
            }

        # Step 2: Organize documents by type
        aggregated_documents = {}
        pending_documents = []
        missing_documents = []
        duplicate_documents = []
        seen_document_types = set()

        for document in documents:

            document_type = document.document_type

            if document_type not in self.REQUIRED_DOCUMENTS:
                logger.warning(
                    "Unknown document type: %s | document_id: %s",
                    document_type,
                    document.id
                )
                continue

            if document_type in seen_document_types:
                duplicate_documents.append({
                    "document_type": document_type,
                    "document_id": document.id,
                    "message": "Multiple documents found for this type"
                })
                continue

            seen_document_types.add(document_type)

            # Step 3: Check document processing status
            if document.status != "completed":
                pending_documents.append({
                    "document_id": document.id,
                    "document_type": document_type,
                    "status": document.status,
                })
                continue

            # Step 4: Check structured extraction result
            if not document.structured_result:
                pending_documents.append({
                    "document_id": document.id,
                    "document_type": document_type,
                    "status": "structured_result_missing",
                })
                continue

            # Step 5: Add normalized document data
            aggregated_documents[document_type] = {
                "document_id": document.id,
                "document_type": document_type,
                "structured_result": document.structured_result,
            }

        # Step 6: Identify missing document types
        available_types = set(aggregated_documents.keys())

        observed_types = {
            document.document_type
            for document in documents
            if document.document_type in self.REQUIRED_DOCUMENTS
        }

        missing_documents = sorted(
            self.REQUIRED_DOCUMENTS - observed_types
        )

        # Step 7: Determine aggregation status
        if duplicate_documents:
            aggregation_status = "needs_review"

        elif pending_documents or missing_documents:
            aggregation_status = "documents_pending"

        elif available_types == self.REQUIRED_DOCUMENTS:
            aggregation_status = "ready_for_validation"

        else:
            aggregation_status = "documents_pending"

        logger.info(
            "Claim aggregation completed: %s | status: %s",
            claim_id,
            aggregation_status
        )

        # Step 8: Return consolidated claim data
        return {
            "claim_id": claim_id,
            "status": aggregation_status,
            "summary": {
                "total_documents_found": len(documents),
                "successfully_processed": len(aggregated_documents),
                "required_documents": len(self.REQUIRED_DOCUMENTS),
            },
            "documents": aggregated_documents,
            "missing_documents": missing_documents,
            "pending_documents": pending_documents,
            "duplicate_documents": duplicate_documents,
        }
