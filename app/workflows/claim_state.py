from typing import TypedDict, Any


class ClaimWorkflowState(TypedDict, total=False):

    claim_id: str
    aggregated_claim: dict[str, Any]

    validation_result: dict[str, Any]
    analysis_result: dict[str, Any]

    workflow_status: str
    next_action: str
    analysis_recommendation: str

    review_decision: str
    reviewer: str
    review_comments: str

    error_message: str