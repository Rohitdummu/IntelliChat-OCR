from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClaimCreate(BaseModel):

    insured_person_name: str = Field(
        min_length=2,
        max_length=150
    )

    policy_number: str = Field(
        min_length=3,
        max_length=100
    )

    patient_name: Optional[str] = None

    hospital_name: Optional[str] = None


class ClaimResponse(BaseModel):

    id: str
    claim_number: str
    insured_person_name: str
    policy_number: str
    patient_name: Optional[str]
    hospital_name: Optional[str]
    status: str
    created_at: datetime