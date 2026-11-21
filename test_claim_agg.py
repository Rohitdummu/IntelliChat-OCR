
import json

from app.core.database import SessionLocal
from app.models.claim import Claim
from app.services.claim_aggregation import ClaimAggregationService


def test_claim_aggregation(claim_number: str):

    db = SessionLocal()

    try:
        # Find claim using its business claim number
        claim = (
            db.query(Claim)
            .filter(Claim.claim_number == claim_number)
            .first()
        )

        if not claim:
            print("Claim not found")
            return

        # Initialize aggregation service
        aggregation_service = ClaimAggregationService(db)

        # Aggregate documents using internal claim ID
        result = aggregation_service.aggregate_claim_documents(
            str(claim.id)
        )

        print("\nCLAIM AGGREGATION RESULT")
        print("=" * 50)

        print(json.dumps(result, indent=4, default=str))

    finally:
        db.close()


if __name__ == "__main__":

    claim_number = input("Enter claim number: ").strip()

    test_claim_aggregation(claim_number)
