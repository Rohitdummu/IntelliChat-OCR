from app.services.validation.validation_rules import (
    validate_patient_name
)
from app.services.validation.validation_rules import (
    validate_patient_name,
    validate_patient_id
)

class ClaimValidationService:

    def validate_claim(self, aggregated_claim):

        documents = aggregated_claim.get("documents", {})

        validation_results = []

        # Rule 1: Patient name
        validation_results.append(
            validate_patient_name(documents)
        )

        # Rule 2: Patient ID
        validation_results.append(
            validate_patient_id(documents)
        )

        failed_checks = [
            result for result in validation_results
            if result["status"] == "failed"
        ]

        unavailable_checks = [
            result for result in validation_results
            if result["status"] == "not_available"
        ]

        if failed_checks:
            overall_status = "needs_review"

        elif unavailable_checks:
            overall_status = "incomplete"

        else:
            overall_status = "validated"

        return {
            "claim_id": aggregated_claim.get("claim_id"),
            "validation_status": overall_status,
            "total_checks": len(validation_results),
            "passed_checks": sum(
                r["status"] == "passed"
                for r in validation_results
            ),
            "failed_checks": len(failed_checks),
            "results": validation_results
        }