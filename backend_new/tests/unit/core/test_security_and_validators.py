from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.validators import (
    normalize_email,
    normalize_optional_non_empty_str,
    normalize_optional_str,
    normalize_required_str,
)


# 验证密码哈希与校验能够正确形成闭环。
def test_hash_and_verify_password_roundtrip() -> None:
    hashed = hash_password("Password123")

    assert hashed != "Password123"
    assert verify_password("Password123", hashed) is True
    assert verify_password("WrongPassword", hashed) is False


# 验证 access token 和 refresh token 会写入正确的 subject 与类型。
def test_access_and_refresh_tokens_encode_expected_payload() -> None:
    access_payload = decode_token(create_access_token("12"))
    refresh_payload = decode_token(create_refresh_token("34"))

    assert access_payload["sub"] == "12"
    assert access_payload["type"] == "access"
    assert refresh_payload["sub"] == "34"
    assert refresh_payload["type"] == "refresh"


# 验证字符串规范化会去除空白并保留有效内容。
def test_normalize_helpers_trim_and_validate() -> None:
    assert normalize_email("  USER@example.com ") == "user@example.com"
    assert normalize_optional_str("  hello  ") == "hello"
    assert normalize_optional_str("   ") is None
    assert normalize_required_str("  value ", field_name="Field") == "value"
    assert (
        normalize_optional_non_empty_str("  value ", field_name="Field") == "value"
    )


# 验证必填字符串规范化会拒绝空白输入。
def test_normalize_required_str_rejects_blank_value() -> None:
    try:
        normalize_required_str("   ", field_name="Field")
    except ValueError as exc:
        assert str(exc) == "Field cannot be empty"
    else:
        raise AssertionError("Expected ValueError for blank required field")
