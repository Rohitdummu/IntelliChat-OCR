
from typing import Any


class FieldMetadataMerger:

    @staticmethod
    def merge(
        fields: dict,
        field_metadata: dict
    ) -> dict:
        """
        Merge Azure field metadata into extracted fields.

        Supports:
        - Primitive fields
        - Nested objects
        - Arrays
        - Objects inside arrays
        """

        def enrich(value: Any, path: str) -> dict:

            metadata = field_metadata.get(path, {})

            # Handle nested objects
            if isinstance(value, dict):

                enriched_value = {}

                for key, child_value in value.items():

                    child_path = f"{path}.{key}"

                    enriched_value[key] = enrich(
                        child_value,
                        child_path
                    )

                result = {
                    "value": enriched_value
                }

            # Handle arrays
            elif isinstance(value, list):

                enriched_value = []

                for index, item in enumerate(value):

                    child_path = f"{path}.{index}"

                    enriched_value.append(
                        enrich(item, child_path)
                    )

                result = {
                    "value": enriched_value
                }

            # Handle primitive values
            else:

                result = {
                    "value": value
                }

            # Attach Azure metadata when available
            for key, metadata_value in metadata.items():

                result[key] = metadata_value

            return result

        enriched_fields = {}

        for field_name, field_value in fields.items():

            enriched_fields[field_name] = enrich(
                field_value,
                field_name
            )

        return enriched_fields
