
from app.agents.validation_agent import ClaimValidationAgent
from app.services.validation.claim_validation import (
    ClaimValidationService
)


# Initialize service and agent
validation_service = ClaimValidationService()

validation_agent = ClaimValidationAgent(
    validation_service=validation_service
)

# Sample state
sample_state = {
    "aggregated_claim": {
        "claim_id": "TEST-001",
        "status": "ready_for_validation",
        "documents": {}
    }
}

# Execute agent
result = validation_agent.execute(sample_state)

print(result)
