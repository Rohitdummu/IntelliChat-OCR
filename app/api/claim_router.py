import logging

from uuid import uuid4
from datetime import datetime, timezone
from typing import AsyncIterator, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.models.document import Document
from app.core.database import get_db
from app.models.claim import Claim
from app.schema.claim import ClaimCreate, ClaimResponse
from app.services.documnt_processor_new import (
    process_document_task_new
)
from pathlib import Path
from app.services.blob_storage import upload_to_blob
from app.services.claim_aggregation import ClaimAggregationService
from app.services.validation.claim_validation import ClaimValidationService

from app.models.claim_review import ClaimReview
from app.schema.claim_review import ClaimReviewRequest
from app.agents.validation_agent import ClaimValidationAgent
from app.agents.caim_analysis_agent import ClaimAnalysisAgent
from app.agents.decision_agent import ClaimDecisionAgent

from app.workflows.claim_workflow import ClaimWorkflowOrchestrator

from app.services.validation.claim_validation import ClaimValidationService
from app.services.azure_openai import AzureOpenAIService
from app.services.claim_aggregation import ClaimAggregationService
from uuid import uuid4

logger = logging.getLogger(__name__)

claim_router = APIRouter(
    prefix="/claims",
    tags=["Claim Documents"]
)

class WorkflowReviewRequest(BaseModel):
    action: Literal[
        "approved",
        "rejected",
        "requires_information"
    ]

    reviewer: str = Field(min_length=1, max_length=150)
    comments: str | None = None

def build_claim_workflow(request: Request):

    validation_agent = ClaimValidationAgent(
        ClaimValidationService()
    )

    analysis_agent = ClaimAnalysisAgent(
        request.app.state.azure_openai_service
    )

    decision_agent = ClaimDecisionAgent()

    return ClaimWorkflowOrchestrator(
        validation_agent=validation_agent,
        analysis_agent=analysis_agent,
        decision_agent=decision_agent,
        checkpointer=request.app.state.checkpointer
    )


@claim_router.post(
    "",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED
)
def create_claim(
    payload: ClaimCreate,
    db: Session = Depends(get_db)
):
    """Create a new health insurance claim."""

    claim_id = str(uuid4())

    claim_number = (
        f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        f"-{uuid4().hex[:8].upper()}"
    )

    logger.info(
        "Creating new claim",
        extra={"claim_id": claim_id}
    )

    try:
        claim = Claim(
            id=claim_id,
            claim_number=claim_number,
            insured_person_name=payload.insured_person_name,
            policy_number=payload.policy_number,
            patient_name=payload.patient_name,
            hospital_name=payload.hospital_name,
            status="awaiting_documents"
        )

        db.add(claim)
        db.commit()
        db.refresh(claim)

        logger.info(
            "Claim created successfully",
            extra={"claim_id": claim.id}
        )

        return claim

    except SQLAlchemyError:
        db.rollback()

        logger.exception(
            "Database error while creating claim"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create claim"
        )
@claim_router.post(
    "/{claim_id}/documents",
    status_code=status.HTTP_201_CREATED
)
async def upload_claim_document(
    claim_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a document against an existing insurance claim."""

    # 1. Verify claim exists
    claim = db.query(Claim).filter(
        Claim.id == claim_id
    ).first()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )

    # 2. Validate file extension
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )

    # 3. Validate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Only PDF files are allowed"
        )

    doc_id = str(uuid4())

    try:
        # 4. Read uploaded file
        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Uploaded file is empty"
            )

        # 5. Validate PDF signature
        if not file_content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file"
            )

        # 6. Upload to Azure Blob Storage
        blob_result = await upload_to_blob(
            file_content=file_content,
            document_id=doc_id
        )

        logger.info(
            "Document uploaded to Blob Storage",
            extra={"document_id": doc_id, "claim_id": claim_id}
        )

        # 7. Create database record
        document = Document(
            id=doc_id,
            claim_id=claim_id,
            filename=file.filename,
            blob_name=blob_result["blob_name"],
            document_type="pending_classification",
            status="uploaded"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(
            "Document metadata saved successfully",
            extra={"document_id": doc_id, "claim_id": claim_id}
        )

        # 8. Return response
        return {
            "document_id": document.id,
            "claim_id": document.claim_id,
            "filename": document.filename,
            "document_type": document.document_type,
            "status": document.status,
            "message": "Document uploaded successfully"
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()

        logger.exception(
            "Database error while saving document metadata"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document metadata"
        )

    except Exception:
        db.rollback()

        logger.exception(
            "Unexpected error during document upload"
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed"
        )

    finally:
        await file.close()

@claim_router.post(
    "/process/{document_id}",
    status_code=status.HTTP_201_CREATED
)
async def process_claim_documents(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    '''
    Endpoint to initiate the processing of a document.
    '''

    # Find document
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(404, "Document not found")

    if document.status in ("queued", "processing"):
        raise HTTPException(
            409,
            f"Document is already {document.status}"
        )

    if document.status == "completed":
        raise HTTPException(
            409,
            "Document is already processed"
        )

    # Mark as queued
    document.status = "queued"
    document.error_message = None
    db.commit()

    # Execute background processing
    background_tasks.add_task(
        process_document_task_new,
        document_id
    )

    return {
        "document_id": document_id,
        "status": "queued",
        "message": "Document processing started"
    }


@claim_router.get(
    "/{claim_id}/aggregate",
    status_code=status.HTTP_200_OK
)
def aggregate_claim(
    claim_id: str,
    db: Session = Depends(get_db)
):
    """
    Aggregate all uploaded documents belonging to a claim.
    """

    # Step 1: Verify claim exists
    claim = db.query(Claim).filter(
        Claim.id == claim_id
    ).first()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Claim not found"
        )

    # Step 2: Initialize aggregation service
    aggregator = ClaimAggregationService(db)

    # Step 3: Aggregate documents
    aggregation_result = aggregator.aggregate_claim_documents(
        str(claim_id)
    )

    logger.info(
        "Claim aggregation completed",
        extra={
            "claim_id": claim_id,
            "aggregation_status": aggregation_result.get("status")
        }
    )

    # Step 4: Return aggregation result
    return aggregation_result

@claim_router.get("/{claim_id}/validate")
def validate_claim(
    claim_id: str,
    db: Session = Depends(get_db)
):
    # Step 1: Check claim exists
    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id)
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    # Step 2: Aggregate claim documents
    aggregation_service = ClaimAggregationService(db)

    aggregated_claim = aggregation_service.aggregate_claim_documents(
        claim_id
    )

    # Step 3: Validate aggregated documents
    validation_service = ClaimValidationService()

    validation_result = validation_service.validate_claim(
        aggregated_claim
    )

    # Step 4: Return 
    
    # Save validation result
    claim.validation_result = validation_result

    # Update claim status
    claim.status = validation_result["validation_status"]

    db.commit()
    db.refresh(claim)

    return {
        "claim_id": claim.id,
        "claim_number": claim.claim_number,
        "validation_result": validation_result
    }


@claim_router.get("/{claim_id}/validation-result")
def get_validation_result(
    claim_id: str,
    db: Session = Depends(get_db)
):
    # Fetch claim
    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id)
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    # Check validation result availability
    if not claim.validation_result:
        raise HTTPException(
            status_code=404,
            detail="Validation result not available for this claim"
        )

    return {
        "claim_id": claim.id,
        "claim_number": claim.claim_number,
        "claim_status": claim.status,
        "validation_result": claim.validation_result
    }



@claim_router.get("/review-queue")
def get_claim_review_queue(
    db: Session = Depends(get_db)
):
    claims = (
        db.query(Claim)
        .filter(Claim.status == "needs_review")
        .order_by(Claim.created_at.desc())
        .all()
    )

    results = []

    for claim in claims:
        results.append({
            "claim_id": claim.id,
            "claim_number": claim.claim_number,
            "patient_name": claim.patient_name,
            "hospital_name": claim.hospital_name,
            "policy_number": claim.policy_number,
            "status": claim.status,
            "document_count": len(claim.documents),
            "validation_summary": {
                "total_checks": claim.validation_result.get("total_checks", 0),
                "passed_checks": claim.validation_result.get("passed_checks", 0),
                "failed_checks": claim.validation_result.get("failed_checks", 0),
            },
            "created_at": claim.created_at
        })

    return {
        "total_claims": len(results),
        "claims": results
    }


@claim_router.get("/{claim_id}/review-details")
def get_claim_review_details(
    claim_id: str,
    db: Session = Depends(get_db)
):
    # 1. Fetch claim
    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id)
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    # 2. Fetch all document versions
    documents = (
        db.query(Document)
        .filter(Document.claim_id == claim_id)
        .order_by(
            Document.document_group_id,
            Document.version.asc()
        )
        .all()
    )

    # 3. Identify latest version of each document group
    latest_versions = {}

    for document in documents:
        group_id = document.document_group_id or document.id

        current = latest_versions.get(group_id)

        if (
            current is None
            or document.version > current.version
        ):
            latest_versions[group_id] = document

    # 4. Prepare document details
    document_details = []

    for document in documents:

        group_id = document.document_group_id or document.id

        latest_document = latest_versions[group_id]

        document_details.append({
            "document_id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,

            # Version information
            "document_group_id": group_id,
            "version": document.version,
            "previous_document_id": document.previous_document_id,
            "is_latest_version": document.id == latest_document.id,

            # Processing information
            "status": document.status,
            "review_status": document.review_status,

            # Extraction information
            "structured_result": document.structured_result,
            "error_message": document.error_message,

            # Resubmission information
            "resubmission_reason": document.resubmission_reason,

            "created_at": document.created_at
        })

    # 5. Calculate summary
    latest_documents = list(latest_versions.values())

    return {
        "claim_details": {
            "claim_id": claim.id,
            "claim_number": claim.claim_number,
            "insured_person_name": claim.insured_person_name,
            "patient_name": claim.patient_name,
            "policy_number": claim.policy_number,
            "hospital_name": claim.hospital_name,
            "status": claim.status,
            "created_at": claim.created_at
        },

        "document_summary": {
            "total_document_versions": len(documents),
            "total_logical_documents": len(latest_documents),
            "processed_latest_documents": sum(
                doc.status == "completed"
                for doc in latest_documents
            ),
            "failed_latest_documents": sum(
                doc.status == "failed"
                for doc in latest_documents
            )
        },

        "documents": document_details,

        "validation_result": claim.validation_result
    }



# @claim_router.get("/{claim_id}/review-details")
# def get_claim_review_details(
#     claim_id: str,
#     db: Session = Depends(get_db)
# ):
#     # Step 1: Fetch claim
#     claim = (
#         db.query(Claim)
#         .filter(Claim.id == claim_id)
#         .first()
#     )

#     if not claim:
#         raise HTTPException(
#             status_code=404,
#             detail="Claim not found"
#         )

#     # Step 2: Fetch associated documents
#     documents = (
#         db.query(Document)
#         .filter(Document.claim_id == claim_id)
#         .order_by(Document.created_at.asc())
#         .all()
#     )

#     # Step 3: Prepare document details
#     document_details = []

#     for document in documents:
#         document_details.append({
#             "document_id": document.id,
#             "filename": document.filename,
#             "document_type": document.document_type,
#             "status": document.status,
#             "structured_result": document.structured_result,
#             "error_message": document.error_message,
#             "created_at": document.created_at
#         })

#     # Step 4: Return review details
#     return {
#         "claim_details": {
#             "claim_id": claim.id,
#             "claim_number": claim.claim_number,
#             "insured_person_name": claim.insured_person_name,
#             "patient_name": claim.patient_name,
#             "policy_number": claim.policy_number,
#             "hospital_name": claim.hospital_name,
#             "status": claim.status,
#             "created_at": claim.created_at
#         },

#         "document_summary": {
#             "total_documents": len(documents),
#             "processed_documents": sum(
#                 doc.status == "completed"
#                 for doc in documents
#             ),
#             "failed_documents": sum(
#                 doc.status == "failed"
#                 for doc in documents
#             )
#         },

#         "documents": document_details,

#         "validation_result": claim.validation_result
#     }


# @claim_router.post("/{claim_id}/review")
# def submit_claim_review(
#     claim_id: str,
#     request: ClaimReviewRequest,
#     db: Session = Depends(get_db)
# ):

#     # Step 1: Fetch claim
#     claim = (
#         db.query(Claim)
#         .filter(Claim.id == claim_id)
#         .first()
#     )

#     if not claim:
#         raise HTTPException(
#             status_code=404,
#             detail="Claim not found"
#         )

#     # Step 2: Ensure validation has been performed
#     if not claim.validation_result:
#         raise HTTPException(
#             status_code=400,
#             detail="Claim has not been validated yet"
#         )

#     # Step 3: Create review record
#     review = ClaimReview(
#         claim_id=claim.id,
#         action=request.action,
#         reviewer=request.reviewer,
#         comments=request.comments
#     )

#     # Step 4: Update claim status
#     claim.status = request.action

#     # Step 5: Save to database
#     try:
#         db.add(review)
#         db.commit()

#         db.refresh(claim)
#         db.refresh(review)

#     except Exception:
#         db.rollback()
#         raise

#     # Step 6: Return response
#     return {
#         "message": "Claim review submitted successfully",
#         "claim_id": claim.id,
#         "claim_number": claim.claim_number,
#         "claim_status": claim.status,
#         "review": {
#             "review_id": review.id,
#             "action": review.action,
#             "reviewer": review.reviewer,
#             "comments": review.comments,
#             "created_at": review.created_at
#         }
#     }


@claim_router.get("/{claim_id}/reviews")
def get_claim_review_history(
    claim_id: str,
    db: Session = Depends(get_db)
):

    # Step 1: Verify claim exists
    claim = (
        db.query(Claim)
        .filter(Claim.id == claim_id)
        .first()
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Claim not found"
        )

    # Step 2: Fetch review history
    reviews = (
        db.query(ClaimReview)
        .filter(ClaimReview.claim_id == claim_id)
        .order_by(ClaimReview.created_at.desc())
        .all()
    )

    # Step 3: Prepare response
    review_history = []

    for review in reviews:
        review_history.append({
            "review_id": review.id,
            "action": review.action,
            "reviewer": review.reviewer,
            "comments": review.comments,
            "created_at": review.created_at
        })

    return {
        "claim_id": claim.id,
        "claim_number": claim.claim_number,
        "current_status": claim.status,
        "total_reviews": len(review_history),
        "review_history": review_history
    }


# @claim_router.post("/{claim_id}/run-workflow")
# def run_claim_workflow(
#     claim_id: str,
#     db: Session = Depends(get_db)
# ):

#     logger.info("Starting complete claim workflow: %s", claim_id)

#     try:

#         # Step 1: Fetch claim
#         claim = (
#             db.query(Claim)
#             .filter(Claim.id == claim_id)
#             .first()
#         )

#         if not claim:
#             raise HTTPException(
#                 status_code=404,
#                 detail="Claim not found"
#             )

#         # Step 2: Aggregate claim documents
#         logger.info("Aggregating claim documents...")

#         aggregated_claim = ClaimAggregationService(
#             db
#         ).aggregate_claim_documents(claim_id)

#         # Step 3: Initialize agents using existing services
#         validation_agent = ClaimValidationAgent(
#             ClaimValidationService()
#         )

#         analysis_agent = ClaimAnalysisAgent(
#             AzureOpenAIService()
#         )

#         decision_agent = ClaimDecisionAgent()

#         # Step 4: Initialize orchestrator
#         orchestrator = ClaimWorkflowOrchestrator(
#             validation_agent=validation_agent,
#             analysis_agent=analysis_agent,
#             decision_agent=decision_agent
#         )

#         # Step 5: Prepare initial workflow state
#         initial_state = {
#             "claim_id": claim_id,
#             "aggregated_claim": aggregated_claim,
#             "validation_result": {},
#             "analysis_result": {},
#             "workflow_status": "",
#             "next_action": "",
#             "analysis_recommendation": "",
#             "error_message": ""
#         }

#         # Step 6: Execute LangGraph
#         logger.info("Executing LangGraph workflow...")

#         result = orchestrator.execute(initial_state)

#         # Step 7: Persist workflow results
#         validation_result = result.get(
#             "validation_result", {}
#         )

#         # Preserve existing validation fields and add AI analysis
#         persisted_result = dict(validation_result)

#         persisted_result["analysis_result"] = result.get(
#             "analysis_result", {}
#         )

#         persisted_result["workflow_status"] = result.get(
#             "workflow_status"
#         )

#         persisted_result["next_action"] = result.get(
#             "next_action"
#         )

#         claim.validation_result = persisted_result
#         claim.status = result.get("workflow_status")

#         db.commit()
#         db.refresh(claim)

#         logger.info(
#             "Claim workflow results saved. Claim ID: %s | Status: %s",
#             claim_id,
#             claim.status
#         )

#         return {
#             "message": "Claim workflow executed successfully",
#             "claim_id": claim_id,
#             "claim_number": claim.claim_number,
#             "workflow_status": result.get("workflow_status"),
#             "next_action": result.get("next_action"),
#             "validation_result": validation_result,
#             "analysis_result": result.get("analysis_result", {})
#         }

#     except HTTPException:
#         raise

#     except Exception:
#         db.rollback()

#         logger.exception(
#             "Claim workflow execution failed: %s",
#             claim_id
#         )

#         raise HTTPException(
#             status_code=500,
#             detail="Claim workflow execution failed"
#         )



@claim_router.post("/{claim_id}/run-workflow")
def run_claim_workflow(
    claim_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # 1. Fetch claim
        claim = (
            db.query(Claim)
            .filter(Claim.id == claim_id)
            .first()
        )

        if not claim:
            raise HTTPException(
                status_code=404,
                detail="Claim not found"
            )

        # 2. Aggregate latest document versions
        aggregated_claim = ClaimAggregationService(
            db
        ).aggregate_claim_documents(claim_id)

        # 3. Ensure documents are ready
        if aggregated_claim.get("status") != "ready_for_validation":
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Claim documents are not ready for validation",
                    "aggregation_status": aggregated_claim.get("status"),
                    "missing_documents": aggregated_claim.get(
                        "missing_documents", []
                    ),
                    "pending_documents": aggregated_claim.get(
                        "pending_documents", []
                    ),
                    "duplicate_documents": aggregated_claim.get(
                        "duplicate_documents", []
                    )
                }
            )

        # 4. Generate a new workflow cycle
        previous_result = dict(claim.validation_result or {})

        workflow_cycle = (
            int(previous_result.get("workflow_cycle", 0)) + 1
        )

        workflow_run_id = str(uuid4())

        thread_id = (
            f"claim-{claim_id}-cycle-{workflow_cycle}-{workflow_run_id}"
        )

        trigger = (
            "document_resubmission"
            if previous_result.get("is_stale")
            else "initial_submission"
        )

        logger.info(
            "Starting workflow | claim=%s | cycle=%s | trigger=%s",
            claim_id,
            workflow_cycle,
            trigger
        )

        # 5. Build orchestrator
        orchestrator = build_claim_workflow(request)

        # 6. Prepare initial state
        initial_state = {
            "claim_id": claim_id,
            "aggregated_claim": aggregated_claim,
            "validation_result": {},
            "analysis_result": {},
            "workflow_status": "",
            "next_action": "",
            "analysis_recommendation": "",
            "review_decision": "",
            "reviewer": "",
            "review_comments": "",
            "workflow_run_id": workflow_run_id,
            "workflow_cycle": workflow_cycle,
            "trigger": trigger,
            "error_message": ""
        }

        # 7. Execute fresh LangGraph workflow
        result = orchestrator.execute(
            initial_state,
            thread_id
        )

        interrupts = result.get("__interrupt__", [])

        validation_result = result.get(
            "validation_result", {}
        )

        analysis_result = result.get(
            "analysis_result", {}
        )

        # 8. Prepare persisted workflow results
        persisted_result = dict(validation_result)

        persisted_result["analysis_result"] = analysis_result
        persisted_result["workflow_run_id"] = workflow_run_id
        persisted_result["workflow_cycle"] = workflow_cycle
        persisted_result["workflow_thread_id"] = thread_id
        persisted_result["trigger"] = trigger
        persisted_result["is_stale"] = False

        claim.validation_result = persisted_result

        # 9. Handle human-review interrupt
        if interrupts:

            claim.status = "needs_review"
            db.commit()

            interrupt_data = interrupts[0].value

            return {
                "message": "Claim requires human review",
                "claim_id": claim_id,
                "workflow_run_id": workflow_run_id,
                "workflow_cycle": workflow_cycle,
                "thread_id": thread_id,
                "workflow_paused": True,
                "workflow_status": "needs_review",
                "review_request": {
                    "message": interrupt_data.get("message"),
                    "allowed_actions": interrupt_data.get(
                        "allowed_actions", []
                    )
                },
                "validation_result": validation_result,
                "analysis_result": analysis_result
            }

        # 10. Handle completed workflow
        claim.status = result.get("workflow_status")

        db.commit()

        return {
            "message": "Workflow completed",
            "claim_id": claim_id,
            "workflow_run_id": workflow_run_id,
            "workflow_cycle": workflow_cycle,
            "thread_id": thread_id,
            "workflow_paused": False,
            "workflow_status": claim.status,
            "validation_result": validation_result,
            "analysis_result": analysis_result
        }

    except HTTPException:
        raise

    except Exception:

        db.rollback()

        logger.exception(
            "Claim workflow failed: %s",
            claim_id
        )

        raise HTTPException(
            status_code=500,
            detail="Claim workflow execution failed"
        )


@claim_router.post("/{claim_id}/run-workflow")
def run_claim_workflow(
    claim_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        # 1. Fetch claim
        claim = (
            db.query(Claim)
            .filter(Claim.id == claim_id)
            .first()
        )

        if not claim:
            raise HTTPException(
                status_code=404,
                detail="Claim not found"
            )

        # 2. Aggregate latest document versions
        aggregated_claim = ClaimAggregationService(
            db
        ).aggregate_claim_documents(claim_id)

        # 3. Ensure documents are ready
        if aggregated_claim.get("status") != "ready_for_validation":
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Claim documents are not ready for validation",
                    "aggregation_status": aggregated_claim.get("status"),
                    "missing_documents": aggregated_claim.get(
                        "missing_documents", []
                    ),
                    "pending_documents": aggregated_claim.get(
                        "pending_documents", []
                    ),
                    "duplicate_documents": aggregated_claim.get(
                        "duplicate_documents", []
                    )
                }
            )

        # 4. Generate a new workflow cycle
        previous_result = dict(claim.validation_result or {})

        workflow_cycle = (
            int(previous_result.get("workflow_cycle", 0)) + 1
        )

        workflow_run_id = str(uuid4())

        thread_id = (
            f"claim-{claim_id}-cycle-{workflow_cycle}-{workflow_run_id}"
        )

        trigger = (
            "document_resubmission"
            if previous_result.get("is_stale")
            else "initial_submission"
        )

        logger.info(
            "Starting workflow | claim=%s | cycle=%s | trigger=%s",
            claim_id,
            workflow_cycle,
            trigger
        )

        # 5. Build orchestrator
        orchestrator = build_claim_workflow(request)

        # 6. Prepare initial state
        initial_state = {
            "claim_id": claim_id,
            "aggregated_claim": aggregated_claim,
            "validation_result": {},
            "analysis_result": {},
            "workflow_status": "",
            "next_action": "",
            "analysis_recommendation": "",
            "review_decision": "",
            "reviewer": "",
            "review_comments": "",
            "workflow_run_id": workflow_run_id,
            "workflow_cycle": workflow_cycle,
            "trigger": trigger,
            "error_message": ""
        }

        # 7. Execute fresh LangGraph workflow
        result = orchestrator.execute(
            initial_state,
            thread_id
        )

        interrupts = result.get("__interrupt__", [])

        validation_result = result.get(
            "validation_result", {}
        )

        analysis_result = result.get(
            "analysis_result", {}
        )

        # 8. Prepare persisted workflow results
        persisted_result = dict(validation_result)

        persisted_result["analysis_result"] = analysis_result
        persisted_result["workflow_run_id"] = workflow_run_id
        persisted_result["workflow_cycle"] = workflow_cycle
        persisted_result["workflow_thread_id"] = thread_id
        persisted_result["trigger"] = trigger
        persisted_result["is_stale"] = False

        claim.validation_result = persisted_result

        # 9. Handle human-review interrupt
        if interrupts:

            claim.status = "needs_review"
            db.commit()

            interrupt_data = interrupts[0].value

            return {
                "message": "Claim requires human review",
                "claim_id": claim_id,
                "workflow_run_id": workflow_run_id,
                "workflow_cycle": workflow_cycle,
                "thread_id": thread_id,
                "workflow_paused": True,
                "workflow_status": "needs_review",
                "review_request": {
                    "message": interrupt_data.get("message"),
                    "allowed_actions": interrupt_data.get(
                        "allowed_actions", []
                    )
                },
                "validation_result": validation_result,
                "analysis_result": analysis_result
            }

        # 10. Handle completed workflow
        claim.status = result.get("workflow_status")

        db.commit()

        return {
            "message": "Workflow completed",
            "claim_id": claim_id,
            "workflow_run_id": workflow_run_id,
            "workflow_cycle": workflow_cycle,
            "thread_id": thread_id,
            "workflow_paused": False,
            "workflow_status": claim.status,
            "validation_result": validation_result,
            "analysis_result": analysis_result
        }

    except HTTPException:
        raise

    except Exception:

        db.rollback()

        logger.exception(
            "Claim workflow failed: %s",
            claim_id
        )

        raise HTTPException(
            status_code=500,
            detail="Claim workflow execution failed"
        )
