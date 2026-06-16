from uuid import uuid4


def build_soft_deleted_unique_value(value: str) -> str:
    normalized_value = str(value).strip()
    return f"{normalized_value}_deleted_{uuid4().hex}"


def build_soft_deleted_optional_unique_value(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = str(value).strip()
    if not normalized_value:
        return None

    return build_soft_deleted_unique_value(normalized_value)
