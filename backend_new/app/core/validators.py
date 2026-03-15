def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if not value:
        raise ValueError("Email cannot be empty")
    return value


def normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def normalize_required_str(value: str, *, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    return value


def normalize_optional_non_empty_str(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} cannot be empty")
    return value