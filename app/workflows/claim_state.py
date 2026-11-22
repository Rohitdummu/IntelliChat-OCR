
from typing import TypedDict, Any


class ClaimWorkflowState(TypedDict, total=False):

    # Claim information
    claim_id: str
    aggregated_claim: dict[str, Any]

    # Validation and analysis
    validation_result: dict[str, Any]
    analysis_result: dict[str, Any]

    # Workflow tracking
    workflow_run_id: str
    workflow_cycle: int
    trigger: str

    workflow_status: str
    next_action: str
    analysis_recommendation: str

    # Human review
    review_decision: str
    reviewer: str
    review_comments: str

    # Error handling
    error_message: str
