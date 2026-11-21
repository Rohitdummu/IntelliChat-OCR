
import logging
import re
from datetime import date, datetime

logger = logging.getLogger(__name__)


class ClaimValidationService:

    CONFIDENCE_THRESHOLD = 0.70

    # Canonical field -> document type -> possible normalized paths
    FIELD_MAPPINGS = {
        "patient_name": {
            "insurance_claim_form": [
                "patient_details.patient_name",
                "primary_insured.full_name",
            ],
            "insurance_claim_form": [
                "patient_details.patient_name",
                "primary_insured.full_name",
            ],
            "discharge_summary": ["patient_name"],
            "hospital_bill": ["patient_name"],
            "laboratory_report": ["patient_name"],
        },
        "patient_id": {
            "insurance_claim_form": ["patient_details.patient_id"],
            "insurance_claim_form": ["patient_details.patient_id"],
            "discharge_summary": ["patient_id"],
            "hospital_bill": ["patient_id"],
            "laboratory_report": ["patient_id"],
        },
        "policy_number": {
            "insurance_claim_form": ["policy_details.policy_number"],
            "insurance_claim_form": ["policy_details.policy_number"],
            "discharge_summary": ["policy_number"],
            "hospital_bill": ["policy_number"],
        },
        "hospital_name": {
            "insurance_claim_form": ["hospitalization_details.hospital_name"],
            "insurance_claim_form": [
                "hospitalization_details.hospital_name"
            ],
            "discharge_summary": ["hospital_name"],
            "hospital_bill": ["hospital_name"],
            "laboratory_report": ["hospital_location"],
        },
        "admission_date": {
            "insurance_claim_form": [
                "hospitalization_details.admission_date"
            ],
            "insurance_claim_form": [
                "hospitalization_details.admission_date"
            ],
            "discharge_summary": ["date_of_admission_date"],
            "hospital_bill": [
                "admission_date",
                "admission_date_time",
            ],
        },
        "discharge_date": {
            "insurance_claim_form": [
                "hospitalization_details.discharge_date"
            ],
            "insurance_claim_form": [
                "hospitalization_details.discharge_date"
            ],
            "discharge_summary": ["date_of_discharge_date"],
            "hospital_bill": [
                "discharge_date",
                "discharge_date_time",
            ],
        },
    }

    def validate_documents(self, documents: list) -> dict:
        """
        Compare normalized fields across documents.

        Each document is expected to have:
        - document_type
        - analysis_result containing normalized JSON
        """

        findings = []

        for field_name, document_mappings in self.FIELD_MAPPINGS.items():

            observations = self._collect_observations(
                documents,
                document_mappings
            )

            if len(observations) < 2:
                continue

            distinct_values = {
                item["normalized_value"]
                for item in observations
            }

            low_confidence = any(
                item["confidence"] is None
                or item["confidence"] < self.CONFIDENCE_THRESHOLD
                for item in observations
            )

            if low_confidence:
                status = "needs_review"
            elif len(distinct_values) == 1:
                status = "matched"
            else:
                status = "mismatch"

            findings.append({
                "field": field_name,
                "status": status,
                "observations": [
                    {
                        "document_id": item["document_id"],
                        "document_type": item["document_type"],
                        "value": item["value"],
                        "confidence": item["confidence"],
                    }
                    for item in observations
                ],
            })

        mismatch_count = sum(
            item["status"] == "mismatch" for item in findings
        )

        review_count = sum(
            item["status"] == "needs_review" for item in findings
        )

        return {
            "status": (
                "needs_review"
                if mismatch_count or review_count
                else "consistent"
            ),
            "summary": {
                "fields_checked": len(findings),
                "mismatches": mismatch_count,
                "needs_review": review_count,
            },
            "findings": findings,
        }

    def _collect_observations(
        self,
        documents: list,
        document_mappings: dict
    ) -> list:

        observations = []

        for document in documents:

            result = document.analysis_result or {}
            document_type = (
                result.get("document_type")
                or document.document_type
                or ""
            ).strip().lower()

            paths = document_mappings.get(document_type, [])

            fields = result.get("fields", {})
            metadata = result.get("field_metadata", {})

            for path in paths:

                value = self._get_nested_value(fields, path)

                if value is None or isinstance(value, (dict, list)):
                    continue

                confidence = metadata.get(path, {}).get("confidence")

                normalized_value = self._normalize_value(value)

                if not normalized_value:
                    continue

                observations.append({
                    "document_id": document.id,
                    "document_type": document_type,
                    "value": value,
                    "normalized_value": normalized_value,
                    "confidence": confidence,
                })

                # Use the first available mapping for this document.
                break

        return observations

    @staticmethod
    def _get_nested_value(data: dict, path: str):
        value = data

        for key in path.split("."):
            if not isinstance(value, dict):
                return None

            value = value.get(key)

            if value is None:
                return None

        return value

    @staticmethod
    def _normalize_value(value) -> str:

        if isinstance(value, (datetime, date)):
            return value.isoformat().lower()

        text = str(value).strip().casefold()

        # Normalize whitespace and punctuation for comparisons.
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text)

        return text.strip()
