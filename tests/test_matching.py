import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Dataset, SourceRecord
from app.services.matching import create_or_update_entity, progressive_search
from app.services.normalizer import normalize_email, normalize_phone, normalize_username


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def add_record(db, dataset, **kwargs):
    rec = SourceRecord(
        dataset_id=dataset.id,
        table_name=kwargs.get("table", "people"),
        row_id=kwargs.get("row_id", "1"),
        raw_json=json.dumps(kwargs.get("raw", {})),
        email_norm=normalize_email(kwargs.get("email", "")),
        phone_norm=normalize_phone(kwargs.get("phone", "")),
        username_norm=normalize_username(kwargs.get("username", "")),
        name_norm=kwargs.get("name", ""),
        member_id_norm=kwargs.get("member_id", ""),
    )
    db.add(rec)
    db.flush()
    return rec


def test_progressive_enrichment_across_sources():
    db = make_session()
    a = Dataset(name="A", source_tag="database_a", status="completed")
    b = Dataset(name="B", source_tag="database_b", status="completed")
    c = Dataset(name="C", source_tag="database_c", status="completed")
    db.add_all([a, b, c])
    db.flush()

    rec_a = add_record(
        db,
        a,
        email="john.carter@example.com",
        phone="4155550198",
        name="John Carter",
        raw={"email": "john.carter@example.com", "mobile_number": "4155550198"},
    )
    rec_b = add_record(
        db,
        b,
        email="john.carter@example.com",
        raw={"email_id": "john.carter@example.com", "address": "12 Market St"},
        row_id="2",
    )
    rec_c = add_record(
        db,
        c,
        phone="4155550198",
        username="jcarter",
        raw={"username": "jcarter", "contact_no": "4155550198", "company": "Northwind Labs"},
        row_id="3",
    )

    mapping_a = {"email": "email", "mobile_number": "phone", "full_name": "name"}
    mapping_b = {"email_id": "email", "address": "address"}
    mapping_c = {"username": "username", "contact_no": "phone", "company": "company"}

    entity, _, _ = create_or_update_entity(db, rec_a, a, mapping_a)
    create_or_update_entity(db, rec_b, b, mapping_b)
    create_or_update_entity(db, rec_c, c, mapping_c)
    db.commit()

    result = progressive_search(db, "john.carter@example.com")
    assert result["records_visited"] >= 3
    assert "database_a" in result["datasets_touched"]
    assert result["entity"]["id"] == entity.id
    assert "email" in result["entity"]["identifiers"]
