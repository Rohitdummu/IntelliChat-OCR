
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ClaimReviewRequest(BaseModel):

    action: Literal[
        "approved",
        "rejected",
        "requires_information"
    ]

    reviewer: str = Field(min_length=1, max_length=150)

    comments: Optional[str] = None
