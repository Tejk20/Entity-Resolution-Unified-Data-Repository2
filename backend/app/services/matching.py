import json
from collections import deque
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Dataset,
    EntityField,
    IdentifierIndex,
    MasterEntity,
    SourceRecord,
)
from app.services.normalizer import (
    guess_identifier_type,
    normalize_email,
    normalize_field,
    normalize_member_id,
    normalize_name,
    normalize_phone,
    normalize_username,
)

MATCH_PRIORITY = ["email", "phone", "username", "member_id"]

IDENTIFIER_NORMALIZERS = {
    "email": normalize_email,
    "phone": normalize_phone,
    "username": normalize_username,
    "member_id": normalize_member_id,
    "name": normalize_name,
}


def _utcnow():
    return datetime.now(timezone.utc)


def find_entity_by_identifier(db: Session, ident_type: str, value: str) -> Optional[MasterEntity]:
    if not value:
        return None
    idx = (
        db.query(IdentifierIndex)
        .filter(
            IdentifierIndex.identifier_type == ident_type,
            IdentifierIndex.normalized_value == value,
        )
        .first()
    )
    if not idx:
        return None
    return db.get(MasterEntity, idx.master_entity_id)


def match_record(db: Session, record: SourceRecord) -> Optional[MasterEntity]:
    candidates = [
        ("email", record.email_norm),
        ("phone", record.phone_norm),
        ("username", record.username_norm),
        ("member_id", record.member_id_norm),
    ]
    for ident_type, value in candidates:
        entity = find_entity_by_identifier(db, ident_type, value)
        if entity:
            return entity
    return None


def _index_identifier(db: Session, entity_id: int, ident_type: str, value: str, record_id: int):
    if not value:
        return
    exists = (
        db.query(IdentifierIndex)
        .filter(
            IdentifierIndex.identifier_type == ident_type,
            IdentifierIndex.normalized_value == value,
            IdentifierIndex.master_entity_id == entity_id,
        )
        .first()
    )
    if exists:
        return
    db.add(
        IdentifierIndex(
            identifier_type=ident_type,
            normalized_value=value,
            master_entity_id=entity_id,
            source_record_id=record_id,
        )
    )


def _add_field(
    db: Session,
    entity: MasterEntity,
    field_name: str,
    original: str,
    normalized: str,
    source_db: str,
    source_table: str,
    row_id: str,
):
    if not original and not normalized:
        return
    existing = (
        db.query(EntityField)
        .filter(
            EntityField.master_entity_id == entity.id,
            EntityField.field_name == field_name,
            EntityField.normalized_value == normalized,
            EntityField.source_db == source_db,
            EntityField.source_table == source_table,
            EntityField.row_id == row_id,
        )
        .first()
    )
    if existing:
        return
    has_primary = (
        db.query(EntityField)
        .filter(
            EntityField.master_entity_id == entity.id,
            EntityField.field_name == field_name,
            EntityField.is_primary.is_(True),
        )
        .first()
        is not None
    )
    db.add(
        EntityField(
            master_entity_id=entity.id,
            field_name=field_name,
            original_value=original,
            normalized_value=normalized,
            source_db=source_db,
            source_table=source_table,
            row_id=row_id,
            timestamp=_utcnow(),
            is_primary=not has_primary,
        )
    )


def merge_record_into_entity(
    db: Session,
    entity: MasterEntity,
    record: SourceRecord,
    dataset: Dataset,
    mapping: dict[str, str],
):
    raw = json.loads(record.raw_json or "{}")
    reverse = {v: k for k, v in mapping.items()}
    ident_map = {
        "email": record.email_norm,
        "phone": record.phone_norm,
        "username": record.username_norm,
        "member_id": record.member_id_norm,
        "name": record.name_norm,
    }
    for canonical, norm_value in ident_map.items():
        source_col = reverse.get(canonical, canonical)
        original = str(raw.get(source_col, "") or raw.get(canonical, "") or "")
        _add_field(
            db,
            entity,
            canonical,
            original,
            norm_value,
            dataset.source_tag or dataset.name,
            record.table_name,
            record.row_id,
        )
        if canonical in MATCH_PRIORITY:
            _index_identifier(db, entity.id, canonical, norm_value, record.id)

    extra_canonical = set(mapping.values()) - set(ident_map.keys())
    for canonical in extra_canonical:
        source_col = reverse.get(canonical)
        if not source_col:
            continue
        original = str(raw.get(source_col, "") or "")
        normalized = normalize_field(canonical, original)
        _add_field(
            db,
            entity,
            canonical,
            original,
            normalized,
            dataset.source_tag or dataset.name,
            record.table_name,
            record.row_id,
        )

    for col, val in raw.items():
        if col.startswith("_"):
            continue
        if col in mapping:
            continue
        original = str(val or "")
        if not original:
            continue
        _add_field(
            db,
            entity,
            col,
            original,
            original.strip(),
            dataset.source_tag or dataset.name,
            record.table_name,
            record.row_id,
        )

    record.master_entity_id = entity.id
    db.flush()
    entity.match_count = (
        db.query(SourceRecord).filter(SourceRecord.master_entity_id == entity.id).count()
    )
    sources = {
        row[0]
        for row in db.query(SourceRecord.dataset_id)
        .filter(SourceRecord.master_entity_id == entity.id)
        .distinct()
        .all()
    }
    entity.source_count = len(sources)
    entity.status = "matched" if entity.source_count > 1 or entity.match_count > 1 else "unmatched"
    if record.name_norm:
        entity.display_name = record.name_norm
    elif not entity.display_name:
        entity.display_name = (
            record.email_norm or record.username_norm or record.member_id_norm or f"Entity #{entity.id}"
        )
    entity.updated_at = _utcnow()


def create_or_update_entity(
    db: Session,
    record: SourceRecord,
    dataset: Dataset,
    mapping: dict[str, str],
) -> tuple[MasterEntity, bool, bool]:
    existing = match_record(db, record)
    is_new = False
    is_duplicate = False
    if existing:
        is_duplicate = True
        merge_record_into_entity(db, existing, record, dataset, mapping)
        return existing, is_new, is_duplicate

    entity = MasterEntity(
        status="unmatched",
        match_count=0,
        source_count=1,
        display_name=record.name_norm
        or record.email_norm
        or record.username_norm
        or record.member_id_norm
        or "Unnamed entity",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(entity)
    db.flush()
    is_new = True
    merge_record_into_entity(db, entity, record, dataset, mapping)
    return entity, is_new, is_duplicate


def extract_identifiers_from_record(record: SourceRecord) -> list[tuple[str, str]]:
    found = []
    for ident_type, value in [
        ("email", record.email_norm),
        ("phone", record.phone_norm),
        ("username", record.username_norm),
        ("member_id", record.member_id_norm),
    ]:
        if value:
            found.append((ident_type, value))
    return found


def progressive_search(db: Session, query: str, identifier_type: Optional[str] = None) -> dict:
    raw = query.strip()
    if not raw:
        return {"query": query, "hops": [], "entity": None, "records_visited": 0, "datasets_touched": []}

    if identifier_type:
        ident_type = identifier_type
    else:
        ident_type = guess_identifier_type(raw) or "username"

    normalizer = IDENTIFIER_NORMALIZERS.get(ident_type, lambda v: v.strip().lower())
    seed_value = normalizer(raw)

    visited_ids: set[int] = set()
    seen_idents: set[tuple[str, str]] = set()
    hops = []
    queue = deque([(ident_type, seed_value, 0)])
    datasets_touched: set[str] = set()
    matched_entity_id: Optional[int] = None

    while queue:
        itype, ivalue, hop = queue.popleft()
        key = (itype, ivalue)
        if not ivalue or key in seen_idents:
            continue
        seen_idents.add(key)

        col = {
            "email": SourceRecord.email_norm,
            "phone": SourceRecord.phone_norm,
            "username": SourceRecord.username_norm,
            "member_id": SourceRecord.member_id_norm,
            "name": SourceRecord.name_norm,
        }.get(itype)
        if col is None:
            continue

        records = db.query(SourceRecord).filter(col == ivalue).all()
        new_idents = []
        new_count = 0
        for rec in records:
            if rec.id in visited_ids:
                continue
            visited_ids.add(rec.id)
            new_count += 1
            if rec.master_entity_id:
                matched_entity_id = rec.master_entity_id
            ds = db.get(Dataset, rec.dataset_id)
            if ds:
                datasets_touched.add(ds.source_tag or ds.name)
            for ntype, nval in extract_identifiers_from_record(rec):
                if (ntype, nval) not in seen_idents:
                    new_idents.append({"identifier_type": ntype, "identifier_value": nval})
                    queue.append((ntype, nval, hop + 1))

        hops.append(
            {
                "hop": hop,
                "identifier_type": itype,
                "identifier_value": ivalue,
                "records_found": new_count,
                "new_identifiers": new_idents,
            }
        )

    entity_payload = None
    if matched_entity_id:
        entity_payload = build_entity_card(db, matched_entity_id)
    elif visited_ids:
        rec = db.get(SourceRecord, next(iter(visited_ids)))
        if rec and rec.master_entity_id:
            entity_payload = build_entity_card(db, rec.master_entity_id)

    return {
        "query": query,
        "hops": hops,
        "entity": entity_payload,
        "records_visited": len(visited_ids),
        "datasets_touched": sorted(datasets_touched),
    }


def build_entity_card(db: Session, entity_id: int) -> Optional[dict]:
    entity = db.get(MasterEntity, entity_id)
    if not entity:
        return None
    fields = (
        db.query(EntityField)
        .filter(EntityField.master_entity_id == entity.id)
        .order_by(EntityField.field_name, EntityField.timestamp)
        .all()
    )
    identifiers: dict[str, list[str]] = {}
    for idx in entity.identifiers:
        identifiers.setdefault(idx.identifier_type, [])
        if idx.normalized_value not in identifiers[idx.identifier_type]:
            identifiers[idx.identifier_type].append(idx.normalized_value)

    merged: dict[str, str] = {}
    field_payload = []
    for f in fields:
        if f.field_name not in merged and f.normalized_value:
            merged[f.field_name] = f.normalized_value
        field_payload.append(
            {
                "field_name": f.field_name,
                "original_value": f.original_value,
                "normalized_value": f.normalized_value,
                "source_db": f.source_db,
                "source_table": f.source_table,
                "row_id": f.row_id,
                "timestamp": f.timestamp,
                "is_primary": f.is_primary,
            }
        )

    records = db.query(SourceRecord).filter(SourceRecord.master_entity_id == entity.id).all()
    linked = []
    seen_link = set()
    for rec in records:
        ds = db.get(Dataset, rec.dataset_id)
        key = (rec.dataset_id, rec.table_name, rec.row_id)
        if key in seen_link:
            continue
        seen_link.add(key)
        linked.append(
            {
                "dataset_id": rec.dataset_id,
                "dataset_name": ds.name if ds else "",
                "source_tag": ds.source_tag if ds else "",
                "table_name": rec.table_name,
                "row_id": rec.row_id,
                "raw": json.loads(rec.raw_json or "{}"),
            }
        )

    return {
        "id": entity.id,
        "status": entity.status,
        "display_name": entity.display_name,
        "match_count": entity.match_count,
        "source_count": entity.source_count,
        "created_at": entity.created_at,
        "updated_at": entity.updated_at,
        "identifiers": identifiers,
        "fields": field_payload,
        "linked_sources": linked,
        "merged": merged,
    }
