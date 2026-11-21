
import logging
from typing import Any

from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ClaimDecisionAgent(BaseAgent):

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:

        claim_id = state.get("claim_id")

        validation_result = state.get("validation_result", {})
        analysis_result = state.get("analysis_result", {})

        validation_status = validation_result.get(
            "validation_status"
        )

        recommended_action = analysis_result.get(
            "recommended_action"
        )

        logger.info(
            "Decision Agent started. Claim ID: %s",
            claim_id
        )

        # Deterministic decision based on validation
        if validation_status == "incomplete":

            workflow_status = "incomplete"
            next_action = "request_information"

        elif validation_status == "needs_review":

            workflow_status = "needs_review"
            next_action = "manual_review"

        elif validation_status == "validated":

            workflow_status = "validated"
            next_action = "continue_processing"

        else:

            workflow_status = "needs_review"
            next_action = "manual_review"

        logger.info(
            "Decision completed. Claim ID: %s | Status: %s | Action: %s",
            claim_id,
            workflow_status,
            next_action
        )

        return {
            "workflow_status": workflow_status,
            "next_action": next_action,
            "analysis_recommendation": recommended_action
        }
