from app.services.mapper import suggest_mapping, suggestions_to_mapping


def test_suggest_mapping_crm_columns():
    cols = ["full_name", "email", "mobile_number", "city"]
    mapping = suggestions_to_mapping(suggest_mapping(cols))
    assert mapping["email"] == "email"
    assert mapping["mobile_number"] == "phone"
    assert mapping["full_name"] == "name"
    assert mapping["city"] == "city"


def test_suggest_mapping_members_sql_columns():
    cols = ["member_id", "email_address", "user_name", "full_name"]
    mapping = suggestions_to_mapping(suggest_mapping(cols))
    assert mapping["email_address"] == "email"
    assert mapping["user_name"] == "username"
    assert mapping["member_id"] == "member_id"
