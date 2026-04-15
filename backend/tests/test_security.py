from app.core.security import create_token, decode_token, hash_password, verify_password


def test_password_hash_and_verify():
    value = "StrongPass123"
    hashed = hash_password(value)
    assert hashed != value
    assert verify_password(value, hashed)


def test_create_and_decode_access_token():
    token = create_token("42", 5, "access")
    payload = decode_token(token, "access")
    assert payload["sub"] == "42"
