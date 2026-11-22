
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
    logger.info("Starting claim document aggregation: %s", claim_id)

    # Fetch documents, newest versions first within each version group.
    documents = (
        self.db.query(Document)
        .filter(Document.claim_id == claim_id)
        .order_by(
            Document.version.desc(),
            Document.created_at.desc()
        )
        .all()
    )

    if not documents:
        return {
            "claim_id": claim_id,
            "status": "documents_pending",
            "message": "No documents uploaded for this claim",
            "documents": {},
            "missing_documents": sorted(self.REQUIRED_DOCUMENTS),
            "pending_documents": [],
            "duplicate_documents": [],
        }

    # Select only the latest version of each logical document.
    latest_by_group = {}

    for document in documents:
        group_id = document.document_group_id or document.id

        if group_id not in latest_by_group:
            latest_by_group[group_id] = document

    latest_documents = list(latest_by_group.values())

    aggregated_documents = {}
    pending_documents = []
    duplicate_documents = []
    seen_document_types = set()

    for document in latest_documents:
        document_type = document.document_type

        if document_type not in self.REQUIRED_DOCUMENTS:
            logger.warning(
                "Unknown document type: %s | document_id: %s",
                document_type,
                document.id
            )
            continue

        # Multiple logical documents of the same type still
        # require review. Different versions do not.
        if document_type in seen_document_types:
            duplicate_documents.append({
                "document_type": document_type,
                "document_id": document.id,
                "version": document.version,
                "message": "Multiple documents found for this type"
            })
            continue

        seen_document_types.add(document_type)

        if document.status != "completed":
            pending_documents.append({
                "document_id": document.id,
                "document_type": document_type,
                "version": document.version,
                "status": document.status,
            })
            continue

        if not document.structured_result:
            pending_documents.append({
                "document_id": document.id,
                "document_type": document_type,
                "version": document.version,
                "status": "structured_result_missing",
            })
            continue

        aggregated_documents[document_type] = {
            "document_id": document.id,
            "document_type": document_type,
            "document_group_id": document.document_group_id,
            "version": document.version,
            "structured_result": document.structured_result,
        }

    available_types = set(aggregated_documents.keys())

    missing_documents = sorted(
        self.REQUIRED_DOCUMENTS - seen_document_types
    )

    if duplicate_documents:
        aggregation_status = "needs_review"
    elif pending_documents or missing_documents:
        aggregation_status = "documents_pending"
    elif available_types == self.REQUIRED_DOCUMENTS:
        aggregation_status = "ready_for_validation"
    else:
        aggregation_status = "documents_pending"

    return {
        "claim_id": claim_id,
        "status": aggregation_status,
        "summary": {
            "total_documents_found": len(documents),
            "latest_documents_found": len(latest_documents),
            "successfully_processed": len(aggregated_documents),
            "required_documents": len(self.REQUIRED_DOCUMENTS),
        },
        "documents": aggregated_documents,
        "missing_documents": missing_documents,
        "pending_documents": pending_documents,
        "duplicate_documents": duplicate_documents,
    }
