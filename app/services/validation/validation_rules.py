
from app.services.validation.field_comparator import (
    get_field_value,
    compare_values
)


def validate_patient_name(documents):

    document_types = [
        "insurance_claim_form",
        "hospital_bill",
        "discharge_summary",
        "laboratory_report"
    ]

    values = {}

    for doc_type in document_types:

        document = documents.get(doc_type)

        if not document:
            continue

        fields = document.get("structured_result", {}).get(
            "fields", {}
        )

        patient_name = get_field_value(
            fields,
            "patient_name"
        )

        if patient_name:
            values[doc_type] = patient_name

    if len(values) < 2:
        return {
            "rule": "patient_name_consistency",
            "status": "not_available",
            "message": "Insufficient patient names for comparison",
            "values": values
        }

    unique_names = {
        str(value).strip().lower()
        for value in values.values()
    }

    status = (
        "passed"
        if len(unique_names) == 1
        else "failed"
    )

    return {
        "rule": "patient_name_consistency",
        "status": status,
        "severity": "critical" if status == "failed" else "none",
        "message": (
            "Patient names match across documents"
            if status == "passed"
            else "Patient name mismatch detected across documents"
        ),
        "values": values
    }


def validate_patient_id(documents):

    def unwrap(value):
        while isinstance(value, dict) and "value" in value:
            value = value["value"]
        return value

    def get_nested_value(data, path):
        current = data

        for key in path:
            current = unwrap(current)

            if not isinstance(current, dict):
                return None

            current = current.get(key)

            if current is None:
                return None

        return unwrap(current)

    # Actual patient ID locations in your extracted documents
    field_paths = {
        "insurance_claim_form": (
            "patient_details",
            "patient_id"
        ),
        "laboratory_report": (
            "patient_id",
        ),
        "hospital_bill": (
            "patient_id",
        ),
        "discharge_summary": (
            "patient_id",
        )
    }

    extracted_values = {}

    for document_type, path in field_paths.items():

        document = documents.get(document_type)

        if not document:
            continue

        structured_result = document.get("structured_result", {})
        fields = structured_result.get("fields", {})

        patient_id = get_nested_value(fields, path)

        if patient_id is not None and str(patient_id).strip():
            extracted_values[document_type] = str(patient_id).strip()

    # Not enough information to compare
    if len(extracted_values) < 2:
        return {
            "rule": "patient_id_consistency",
            "status": "not_available",
            "severity": "medium",
            "message": "Insufficient patient ID information across documents",
            "values": extracted_values
        }

    # Normalize IDs before comparison
    normalized_values = {
        value.casefold()
        for value in extracted_values.values()
    }

    if len(normalized_values) == 1:
        return {
            "rule": "patient_id_consistency",
            "status": "passed",
            "severity": "none",
            "message": "Patient ID matches across documents",
            "values": extracted_values
        }

    return {
        "rule": "patient_id_consistency",
        "status": "failed",
        "severity": "critical",
        "message": "Patient ID mismatch detected across documents",
        "values": extracted_values
    }

