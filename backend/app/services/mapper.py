import os
import re
from typing import Optional

from app.schemas import MappingSuggestion

CANONICAL_FIELDS = [
    "email",
    "phone",
    "name",
    "username",
    "member_id",
    "address",
    "company",
    "city",
    "country",
    "age",
    "gender",
    "dob",
]

SYNONYMS: dict[str, list[str]] = {
    "email": [
        "email",
        "email_id",
        "emailid",
        "emailaddress",
        "e_mail",
        "mail",
        "emailaddr",
        "primaryemail",
        "useremail",
        "contactemail",
    ],
    "phone": [
        "phone",
        "phonenumber",
        "mobile",
        "mobilenumber",
        "contactno",
        "contactnumber",
        "cellphone",
        "tel",
        "telephone",
        "msisdn",
        "whatsapp",
        "phone_no",
        "ph",
    ],
    "name": [
        "name",
        "fullname",
        "full_name",
        "customername",
        "username_display",
        "displayname",
        "firstname",
        "lastname",
        "personname",
    ],
    "username": [
        "username",
        "user_name",
        "userid",
        "login",
        "handle",
        "screenname",
        "nickname",
        "alias",
    ],
    "member_id": [
        "memberid",
        "member_id",
        "userid",
        "user_id",
        "customerid",
        "custid",
        "accountid",
        "id",
        "pk",
        "primarykey",
    ],
    "address": ["address", "addr", "street", "location", "residence", "homeaddress"],
    "company": ["company", "org", "organization", "employer", "firm", "workplace"],
    "city": ["city", "town", "locality"],
    "country": ["country", "nation", "countrycode"],
    "age": ["age"],
    "gender": ["gender", "sex"],
    "dob": ["dob", "dateofbirth", "birthdate", "birthday"],
}


def _slug(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", col.lower())


def rule_based_map(column: str) -> MappingSuggestion:
    slug = _slug(column)
    best: Optional[str] = None
    best_score = 0.0
    reason = "no synonym match"

    for canonical, aliases in SYNONYMS.items():
        for alias in aliases:
            alias_slug = _slug(alias)
            if slug == alias_slug:
                return MappingSuggestion(
                    source_column=column,
                    canonical_field=canonical,
                    confidence=0.98,
                    reason=f"exact synonym match for {canonical}",
                )
            if alias_slug in slug or slug in alias_slug:
                score = min(len(alias_slug), len(slug)) / max(len(alias_slug), len(slug))
                if score > best_score:
                    best = canonical
                    best_score = score * 0.85
                    reason = f"partial synonym overlap with {canonical}"

    if best and best_score >= 0.4:
        return MappingSuggestion(
            source_column=column,
            canonical_field=best,
            confidence=round(best_score, 2),
            reason=reason,
        )
    return MappingSuggestion(
        source_column=column,
        canonical_field=None,
        confidence=0.0,
        reason=reason,
    )


def llm_refine(column: str, suggestion: MappingSuggestion) -> MappingSuggestion:
    api_key = os.getenv("USER_LLM_API_KEY", "")
    base_url = os.getenv("USER_LLM_BASE_URL", "")
    model = os.getenv("USER_LLM_MODEL", "deepseek-chat")
    if not api_key or not base_url:
        return suggestion
    try:
        import httpx

        prompt = (
            "Map this source column name to one canonical field if appropriate. "
            f"Column: {column}. Canonical options: {', '.join(CANONICAL_FIELDS)}. "
            "Reply with only the canonical field name or NONE."
        )
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You map database column names to a canonical schema."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": 16,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=8.0) as client:
            resp = client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"].strip().lower()
        text = re.sub(r"[^a-z_]", "", text.replace(" ", "_"))
        if text in CANONICAL_FIELDS:
            return MappingSuggestion(
                source_column=column,
                canonical_field=text,
                confidence=max(suggestion.confidence, 0.9),
                reason="llm semantic match",
            )
    except Exception:
        return suggestion
    return suggestion


def suggest_mapping(columns: list[str]) -> list[MappingSuggestion]:
    used: set[str] = set()
    results: list[MappingSuggestion] = []
    for col in columns:
        suggestion = rule_based_map(col)
        if suggestion.canonical_field in used:
            suggestion = MappingSuggestion(
                source_column=col,
                canonical_field=None,
                confidence=0.0,
                reason=f"{suggestion.canonical_field} already assigned",
            )
        elif suggestion.confidence < 0.6:
            suggestion = llm_refine(col, suggestion)
        if suggestion.canonical_field:
            used.add(suggestion.canonical_field)
        results.append(suggestion)
    return results


def suggestions_to_mapping(suggestions: list[MappingSuggestion]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for s in suggestions:
        if s.canonical_field:
            mapping[s.source_column] = s.canonical_field
    return mapping
