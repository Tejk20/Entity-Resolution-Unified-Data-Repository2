import re
from typing import Optional

import phonenumbers


EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.I)
NON_DIGIT = re.compile(r"\D+")
WHITESPACE = re.compile(r"\s+")


def clean_null(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"null", "none", "nan", "n/a", "na", "-", ""}:
        return ""
    return text


def normalize_email(value) -> str:
    text = clean_null(value).lower()
    text = WHITESPACE.sub("", text)
    return text


def normalize_username(value) -> str:
    text = clean_null(value).lower()
    text = WHITESPACE.sub("", text)
    return text


def normalize_name(value) -> str:
    text = clean_null(value)
    text = WHITESPACE.sub(" ", text).strip()
    return " ".join(part.capitalize() for part in text.split(" ")) if text else ""


def normalize_member_id(value) -> str:
    text = clean_null(value).upper()
    text = WHITESPACE.sub("", text)
    return text


def normalize_phone(value, default_region: str = "IN") -> str:
    text = clean_null(value)
    if not text:
        return ""
    digits = NON_DIGIT.sub("", text)
    if not digits:
        return ""
    regions = [default_region, "US", "GB", "IN", "MX", "CN", "AE"]
    seen = set()
    for region in regions:
        if region in seen:
            continue
        seen.add(region)
        try:
            parsed = phonenumbers.parse(text, region)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.NumberParseException:
            continue
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if text.startswith("+") and digits:
        return f"+{digits}"
    return digits


NORMALIZERS = {
    "email": normalize_email,
    "phone": normalize_phone,
    "username": normalize_username,
    "name": normalize_name,
    "member_id": normalize_member_id,
}


def normalize_field(canonical: str, value) -> str:
    fn = NORMALIZERS.get(canonical)
    if fn:
        return fn(value)
    return clean_null(value)


def guess_identifier_type(value: str) -> Optional[str]:
    text = clean_null(value)
    if not text:
        return None
    if "@" in text and EMAIL_RE.match(text.replace(" ", "")):
        return "email"
    digits = NON_DIGIT.sub("", text)
    if digits and 10 <= len(digits) <= 15 and (text.startswith("+") or digits.isdigit()):
        if any(ch.isdigit() for ch in text) and not any(c.isalpha() for c in text.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")):
            return "phone"
    if re.match(r"^(MEM|USR|CUST|ID)[-_]?\w+$", text, re.I):
        return "member_id"
    if re.match(r"^[\w.\-]{3,40}$", text) and "@" not in text:
        return "username"
    return None
