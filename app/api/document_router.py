from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends, BackgroundTasks
from uuid import uuid4
from pathlib import Path
from app.services.blob_storage import upload_to_blob
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.document import Document
from app.services.blob_storage import upload_to_blob
from app.services.document_processor import (
    process_document_task
)
from app.services.documnt_processor_new import (
    process_document_task_new
)
import logging
from sqlalchemy.exc import SQLAlchemyError
from app.models.claim import Claim


logger = logging.getLogger(__name__)

document_router = APIRouter(
    prefix="/ocr",
    tags=["OCR"]
)

# claim_document_router = APIRouter(
#     prefix="/claims",
#     tags=["Claim Documents"]
# )

@document_router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    '''to upload a document for OCR processing and to store in azure blob storage'''

    # validate file extension only pdf is allowed
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF files are allowed.",
        )
    # valiate content type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Only PDF files are allowed.",
        )

    # Generate unique document ID
    doc_id = str(uuid4())

    try:
        # Read uploaded file
        file_content = await file.read()

        if not file_content:
            raise HTTPException(
                detail="uploaded file is empty",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
            )

        # UPLOAD TO BOB
        blob_result = await upload_to_blob(
            file_content=file_content,
            document_id=doc_id
        )
        print(f"Blob upload result: {blob_result}")

        document = Document(
            id=doc_id,
            filename=file.filename,
            blob_name=blob_result["blob_name"],
            status="uploaded"
        )

        db.add(document)
        db.commit()
        db.refresh(document)
        # return resut
        return {
            "document_id": doc_id,
            "file_name": file.filename,
            "status": "uploaded",
            "blob_name": blob_result["blob_name"],
            "message": "doc process step 1 completed"
        }

    except Exception as e:
        print(f"Error uploading document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document upload failed"
        ) from e

    finally:
        await file.close()

    


# 2. Process document
@document_router.post(
    "/process/{document_id}",
    status_code=status.HTTP_202_ACCEPTED
)
async def process_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):

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
        process_document_task,
        document_id
    )

    return {
        "document_id": document_id,
        "status": "queued",
        "message": "Document processing started"
    }


# 3. Get document status and result
@document_router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):

    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(404, "Document not found")

    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status,
        "analysis_result": document.analysis_result,
        "error_message": document.error_message,
        "created_at": document.created_at,
        "updated_at": document.updated_at
    }


# @claim_document_router.post(
#     "/{claim_id}/documents",
#     status_code=status.HTTP_201_CREATED
# )
# async def upload_claim_document(
#     claim_id: str,
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db)
# ):
#     """Upload a document against an existing insurance claim."""

#     # 1. Verify claim exists
#     claim = db.query(Claim).filter(
#         Claim.id == claim_id
#     ).first()

#     if not claim:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Claim not found"
#         )

#     # 2. Validate file extension
#     if Path(file.filename or "").suffix.lower() != ".pdf":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Only PDF files are allowed"
#         )

#     # 3. Validate content type
#     if file.content_type != "application/pdf":
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid content type. Only PDF files are allowed"
#         )

#     doc_id = str(uuid4())

#     try:
#         # 4. Read uploaded file
#         file_content = await file.read()

#         if not file_content:
#             raise HTTPException(
#                 status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
#                 detail="Uploaded file is empty"
#             )

#         # 5. Validate PDF signature
#         if not file_content.startswith(b"%PDF-"):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Invalid PDF file"
#             )

#         # 6. Upload to Azure Blob Storage
#         blob_result = await upload_to_blob(
#             file_content=file_content,
#             document_id=doc_id
#         )

#         logger.info(
#             "Document uploaded to Blob Storage",
#             extra={"document_id": doc_id, "claim_id": claim_id}
#         )

#         # 7. Create database record
#         document = Document(
#             id=doc_id,
#             claim_id=claim_id,
#             filename=file.filename,
#             blob_name=blob_result["blob_name"],
#             document_type="pending_classification",
#             status="uploaded"
#         )

#         db.add(document)
#         db.commit()
#         db.refresh(document)

#         logger.info(
#             "Document metadata saved successfully",
#             extra={"document_id": doc_id, "claim_id": claim_id}
#         )

#         # 8. Return response
#         return {
#             "document_id": document.id,
#             "claim_id": document.claim_id,
#             "filename": document.filename,
#             "document_type": document.document_type,
#             "status": document.status,
#             "message": "Document uploaded successfully"
#         }

#     except HTTPException:
#         raise

#     except SQLAlchemyError:
#         db.rollback()

#         logger.exception(
#             "Database error while saving document metadata"
#         )

#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to save document metadata"
#         )

#     except Exception:
#         db.rollback()

#         logger.exception(
#             "Unexpected error during document upload"
#         )

#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Document upload failed"
#         )

#     finally:
#         await file.close()

# @claim_document_router.post(
#     "/process/{document_id}",
#     status_code=status.HTTP_201_CREATED
# )
# async def process_claim_documents(
#     document_id: str,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db)
# ):
#     # Find document
#     document = db.query(Document).filter(
#         Document.id == document_id
#     ).first()

#     if not document:
#         raise HTTPException(404, "Document not found")

#     if document.status in ("queued", "processing"):
#         raise HTTPException(
#             409,
#             f"Document is already {document.status}"
#         )

#     if document.status == "completed":
#         raise HTTPException(
#             409,
#             "Document is already processed"
#         )

#     # Mark as queued
#     document.status = "queued"
#     document.error_message = None
#     db.commit()

#     # Execute background processing
#     background_tasks.add_task(
#         process_document_task_new,
#         document_id
#     )

#     return {
#         "document_id": document_id,
#         "status": "queued",
#         "message": "Document processing started"
#     }