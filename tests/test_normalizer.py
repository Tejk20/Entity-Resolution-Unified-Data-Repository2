from app.services.normalizer import (
    guess_identifier_type,
    normalize_email,
    normalize_member_id,
    normalize_name,
    normalize_phone,
    normalize_username,
)


def test_normalize_email():
    assert normalize_email("  John.Carter@Example.COM ") == "john.carter@example.com"
    assert normalize_email("null") == ""
    assert normalize_email(None) == ""


def test_normalize_phone_india():
    assert normalize_phone("9876543210") == "+919876543210"
    assert normalize_phone("09876543210") == "+919876543210"
    assert normalize_phone("+91 98765 43210") == "+919876543210"


def test_normalize_username_and_name():
    assert normalize_username("  JCarter ") == "jcarter"
    assert normalize_name("john   carter") == "John Carter"


def test_normalize_member_id():
    assert normalize_member_id(" mem-1001 ") == "MEM-1001"


def test_guess_identifier_type():
    assert guess_identifier_type("john.carter@example.com") == "email"
    assert guess_identifier_type("+14155550198") == "phone"
    assert guess_identifier_type("MEM-1001") == "member_id"
    assert guess_identifier_type("jcarter") == "username"
