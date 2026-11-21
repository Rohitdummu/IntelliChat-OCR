
import logging
import re
import math

logger = logging.getLogger(__name__)


class ExtractionNormalizer:

    VALUE_KEYS = (
        "valueString",
        "valueNumber",
        "valueInteger",
        "valueBoolean",
        "valueDate",
        "valueTime",
    )

    EVIDENCE_KEYS = (
        "confidence",
        "spans",
        "source",
        "type",
    )

    def to_snake_case(self, name: str) -> str:
        # Handle acronyms: IPNumber -> IP_Number
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)

        # Handle PascalCase: PatientName -> Patient_Name
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

        return name.lower()

    def normalize(
        self,
        response: dict,
        document_type: str
    ) -> dict:

        contents = response.get("result", {}).get("contents", [])

        if not contents:
            raise ValueError(
                "No extracted content found in Azure response"
            )

        normalized_fields = {}
        field_metadata = {}
        confidence_scores = []

        for content in contents:

            azure_fields = content.get("fields", {})

            for field_name, field_data in azure_fields.items():

                normalized_name = self.to_snake_case(field_name)

                normalized_fields[normalized_name] = (
                    self._normalize_field(
                        field_data=field_data,
                        field_path=normalized_name,
                        metadata=field_metadata,
                        confidence_scores=confidence_scores,
                    )
                )

        overall_confidence = None

        if confidence_scores:
            overall_confidence = round(
                sum(confidence_scores) / len(confidence_scores),
                4
            )

        return {
            "document_type": document_type,
            "fields": normalized_fields,
            "field_metadata": field_metadata,
            "overall_confidence": overall_confidence,
            "confidence_field_count": len(confidence_scores),
        }

    def _normalize_field(
        self,
        field_data: dict,
        field_path: str,
        metadata: dict,
        confidence_scores: list,
    ):

        if not isinstance(field_data, dict):
            return field_data

        evidence = {}

        for key in self.EVIDENCE_KEYS:
            if key in field_data:
                evidence[key] = field_data[key]

        confidence = field_data.get("confidence")

        # Handle nested objects
        if "valueObject" in field_data:

            normalized_object = {}

            for key, value in field_data["valueObject"].items():

                normalized_key = self.to_snake_case(key)

                nested_path = f"{field_path}.{normalized_key}"

                normalized_object[normalized_key] = (
                    self._normalize_field(
                        field_data=value,
                        field_path=nested_path,
                        metadata=metadata,
                        confidence_scores=confidence_scores,
                    )
                )

            if evidence:
                metadata[field_path] = evidence

            return normalized_object

        # Handle arrays, including arrays of nested objects
        if "valueArray" in field_data:

            normalized_array = []

            for index, item in enumerate(field_data["valueArray"]):

                nested_path = f"{field_path}.{index}"

                normalized_array.append(
                    self._normalize_field(
                        field_data=item,
                        field_path=nested_path,
                        metadata=metadata,
                        confidence_scores=confidence_scores,
                    )
                )

            if evidence:
                metadata[field_path] = evidence

            return normalized_array

        # Handle primitive typed values
        for key in self.VALUE_KEYS:

            if key in field_data:

                if self._is_valid_confidence(confidence):
                    confidence_scores.append(float(confidence))

                if evidence:
                    metadata[field_path] = evidence

                return field_data[key]

        # Preserve unrecognized Azure field structures
        if evidence:
            metadata[field_path] = evidence

        logger.warning(
            "Unrecognized Azure field structure: %s",
            field_path
        )

        return field_data

    @staticmethod
    def _is_valid_confidence(confidence) -> bool:

        if isinstance(confidence, bool):
            return False

        if not isinstance(confidence, (int, float)):
            return False

        return (
            math.isfinite(confidence)
            and 0 <= confidence <= 1
        )


