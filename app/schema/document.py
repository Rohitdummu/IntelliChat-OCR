from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentUploadResponse(BaseModel):
    document_id: str
    claim_id: str
    filename: str
    document_type: Optional[str] = None
    status: str
    message: str