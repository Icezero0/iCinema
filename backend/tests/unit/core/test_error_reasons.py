import re

from app.core.error_reasons import ErrorReason


def test_error_reason_values_are_unique_and_snake_case() -> None:
    values = [reason.value for reason in ErrorReason]

    assert len(values) == len(set(values))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", value) for value in values)
