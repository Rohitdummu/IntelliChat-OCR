
from app.core.database import SessionLocal
from app.models.claim import Claim
from app.models.document import Document
from app.services.claim_validation import ClaimValidationService


def test_claim_validation(claim_number: str):

    db = SessionLocal()

    try:
        # Find the claim
        claim = (
            db.query(Claim)
            .filter(Claim.claim_number == claim_number)
            .first()
        )

        if not claim:
            print("Claim not found")
            return

        # Fetch successfully processed documents
        documents = (
            db.query(Document)
            .filter(
                Document.claim_id == claim.id,
                Document.status == "completed"
            )
            .all()
        )

        if not documents:
            print("No completed documents found")
            return

        print(f"Claim: {claim.claim_number}")
        print(f"Documents found: {len(documents)}")
        for document in documents:
            print("\nDOCUMENT:", document.document_type)

            result = document.analysis_result or {}

            print("Result keys:", result.keys())
            print("Result document type:", result.get("document_type"))

            fields = result.get("fields", {})

            print("Available fields:", list(fields.keys()))
            print("Patient name:", fields.get("patient_name"))
            print("Patient details:", fields.get("patient_details"))

        # Run validation
        validator = ClaimValidationService()

        report = validator.validate_documents(documents)

        print("\nVALIDATION REPORT")
        print("=" * 50)

        import json
        print(json.dumps(report, indent=4, default=str))

    finally:
        db.close()


if __name__ == "__main__":
    claim_number = input("Enter claim number: ").strip()
    test_claim_validation(claim_number)
