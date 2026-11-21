
from typing import Any

from app.agents.base_agent import BaseAgent
from app.services.validation.claim_validation import (
    ClaimValidationService
)


class ClaimValidationAgent(BaseAgent):

    def __init__(
        self,
        validation_service: ClaimValidationService
    ):
        self.validation_service = validation_service

    def execute(
        self,
        state: dict[str, Any]
    ) -> dict[str, Any]:

        aggregated_claim = state["aggregated_claim"]

        validation_result = (
            self.validation_service.validate_claim(
                aggregated_claim
            )
        )

        return {
            "validation_result": validation_result
        }
