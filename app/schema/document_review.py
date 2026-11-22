
from pydantic import BaseModel, Field


class ResubmissionRequest(BaseModel):
    reason: str = Field(
        ...,
        min_length=5,
        max_length=2000
    )

    reviewer: str = Field(
        ...,
        min_length=2,
        max_length=150
    )
