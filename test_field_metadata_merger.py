
from app.core.field_metadata_merger import FieldMetadataMerger


def test_field_metadata_merger():

    fields = {
        "patient_name": "Arjun Kumar Reddy",
        "billing_reference": {
            "total_bill_amount": 82500
        },
        "discharge_medications": [
            {
                "medicine_name": "Paracetamol 500 mg"
            }
        ]
    }

    metadata = {
        "patient_name": {
            "confidence": 0.958,
            "type": "string"
        },
        "billing_reference": {
            "type": "object"
        },
        "billing_reference.total_bill_amount": {
            "confidence": 0.636,
            "type": "number"
        },
        "discharge_medications": {
            "type": "array"
        },
        "discharge_medications.0": {
            "type": "object"
        },
        "discharge_medications.0.medicine_name": {
            "confidence": 0.85,
            "type": "string"
        }
    }

    result = FieldMetadataMerger.merge(
        fields,
        metadata
    )

    assert result["patient_name"]["value"] == "Arjun Kumar Reddy"

    assert (
        result["patient_name"]["confidence"] == 0.958
    )

    assert (
        result["billing_reference"]["value"]
        ["total_bill_amount"]["confidence"] == 0.636
    )

    assert (
        result["discharge_medications"]["value"][0]
        ["value"]["medicine_name"]["confidence"] == 0.85
    )

    print("Metadata merger test passed!")


if __name__ == "__main__":
    test_field_metadata_merger()
