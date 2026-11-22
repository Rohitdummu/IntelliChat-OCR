
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.claim_review import ClaimReview
from app.schema.document_review import ResubmissionRequest
from app.services.documnt_processor_new import (
    process_document_task_new
)
from uuid import uuid4
from app.services.blob_storage import upload_to_blob

review_router = APIRouter(
    prefix="/documents",
    tags=["Document Review"]
)


@review_router.post("/{document_id}/request-resubmission")
def request_document_resubmission(
    document_id: str,
    payload: ResubmissionRequest,
    db: Session = Depends(get_db)
):

    # 1. Find document
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # 2. Ensure document belongs to a claim
    if not document.claim_id:
        raise HTTPException(
            status_code=400,
            detail="Document is not associated with a claim"
        )

    # 3. Prevent duplicate pending requests
    if document.review_status == "resubmission_requested":
        raise HTTPException(
            status_code=409,
            detail="Resubmission has already been requested"
        )

    try:
        # 4. Update document review status
        document.review_status = "resubmission_requested"
        document.resubmission_reason = payload.reason

        # 5. Record reviewer action
        review = ClaimReview(
            claim_id=document.claim_id,
            action="request_resubmission",
            reviewer=payload.reviewer,
            comments=payload.reason
        )

        db.add(review)

        # 6. Commit both changes together
        db.commit()
        db.refresh(document)

        return {
            "document_id": document.id,
            "claim_id": document.claim_id,
            "review_status": document.review_status,
            "resubmission_reason": document.resubmission_reason,
            "message": "Document resubmission requested successfully"
        }

    except Exception:
        db.rollback()
        raise


@review_router.post("/{document_id}/resubmit", status_code=201)
async def resubmit_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Find the original document
    original = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not original:
        raise HTTPException(
            status_code=404,
            detail="Original document not found"
        )

    # 2. Verify resubmission was requested
    if original.review_status != "resubmission_requested":
        raise HTTPException(
            status_code=409,
            detail="Document does not have a pending resubmission request"
        )

    if not original.claim_id:
        raise HTTPException(
            status_code=400,
            detail="Document is not associated with a claim"
        )

    # 3. Ensure this is the latest document version
    latest = (
        db.query(Document)
        .filter(
            Document.document_group_id == original.document_group_id
        )
        .order_by(Document.version.desc())
        .first()
    )

    if latest.id != original.id:
        raise HTTPException(
            status_code=409,
            detail="Resubmission must be made against the latest document version"
        )

    # 4. Validate PDF
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    file_content = await file.read(20 * 1024 * 1024 + 1)

    if not file_content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    if len(file_content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds the 20 MB upload limit"
        )

    if not file_content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Only valid PDF files are accepted"
        )

    # 5. Generate a new document ID
    new_document_id = str(uuid4())

    try:
        # 6. Upload corrected PDF to Azure Blob
        blob_result = await upload_to_blob(
            file_content=file_content,
            document_id=new_document_id
        )

        # 7. Create a new version record
        new_document = Document(
            id=new_document_id,
            filename=file.filename,
            blob_name=blob_result["blob_name"],
            claim_id=original.claim_id,
            document_type=None,
            document_group_id=original.document_group_id,
            version=original.version + 1,
            previous_document_id=original.id,
            status="queued",
            review_status="not_reviewed",
            resubmission_reason=None,
            analysis_result=None,
            structured_result=None,
            error_message=None
        )

        db.add(new_document)

        # 8. Record resubmission in claim history
        review = ClaimReview(
            claim_id=original.claim_id,
            action="document_resubmitted",
            reviewer="system",
            comments=(
                f"New document version {new_document.version} "
                f"uploaded: {file.filename}"
            )
        )

        db.add(review)
        

        # 9. Save database records
        db.commit()
        db.refresh(new_document)

        # 10. Trigger existing OCR processing
        background_tasks.add_task(
            process_document_task_new,
            new_document_id
        )

        return {
            "document_id": new_document.id,
            "claim_id": new_document.claim_id,
            "previous_document_id": new_document.previous_document_id,
            "document_group_id": new_document.document_group_id,
            "version": new_document.version,
            "status": new_document.status,
            "review_status": new_document.review_status,
            "blob_name": new_document.blob_name,
            "message": "Document resubmitted and OCR processing queued"
        }

    except HTTPException:
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Document resubmission failed"
        )


