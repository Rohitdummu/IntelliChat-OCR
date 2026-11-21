
def get_field_value(fields: dict, field_path: str):
    """
    Retrieve a field using a dotted path.
    Unwrap enriched field values.
    """

    current = fields

    for key in field_path.split("."):

        if isinstance(current, dict):
            current = current.get(key)

        elif isinstance(current, list):
            current = current[int(key)]

        else:
            return None

        if current is None:
            return None

    # Unwrap enriched value
    if isinstance(current, dict) and "value" in current:
        return current["value"]

    return current


def normalize_text(value):
    if value is None:
        return None

    return " ".join(str(value).strip().lower().split())


def compare_values(value1, value2):

    normalized1 = normalize_text(value1)
    normalized2 = normalize_text(value2)

    if not normalized1 or not normalized2:
        return "not_available"

    if normalized1 == normalized2:
        return "matched"

    return "mismatched"
