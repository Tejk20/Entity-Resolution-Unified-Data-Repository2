import json
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Dataset, ProcessingJob, SourceRecord, SourceTable
from app.services.mapper import suggest_mapping, suggestions_to_mapping
from app.services.matching import create_or_update_entity
from app.services.normalizer import normalize_email, normalize_member_id, normalize_name, normalize_phone, normalize_username
from app.services.parser import iter_chunks, load_file

STAGES = [
    "uploaded",
    "inspecting",
    "field_mapping",
    "cleaning",
    "indexing",
    "matching",
    "enriching",
    "completed",
]


def _utcnow():
    return datetime.now(timezone.utc)


def set_job(db: Session, job: ProcessingJob, stage: str, progress: float, message: str, **kwargs):
    job.stage = stage
    job.progress = progress
    job.message = message
    for k, v in kwargs.items():
        setattr(job, k, v)
    if stage == "completed":
        job.finished_at = _utcnow()
        job.progress = 100.0
    db.commit()
    db.refresh(job)


def inspect_dataset(db: Session, dataset: Dataset) -> list[SourceTable]:
    tables: list[SourceTable] = []
    for existing_table in db.query(SourceTable).filter(SourceTable.dataset_id == dataset.id).all():
        existing_table.row_count = 0
    for f in dataset.files:
        path = Path(f.filename)
        if not path.exists():
            continue
        parsed = load_file(path)
        for table_name, columns, rows in parsed:
            mapping_suggestions = suggest_mapping(columns)
            mapping = suggestions_to_mapping(mapping_suggestions)
            existing = (
                db.query(SourceTable)
                .filter(SourceTable.dataset_id == dataset.id, SourceTable.table_name == table_name)
                .first()
            )
            if existing:
                existing.columns_json = json.dumps(columns)
                if not existing.mapping_confirmed:
                    existing.mapping_json = json.dumps(mapping)
                existing.row_count = (existing.row_count or 0) + len(rows)
                if existing not in tables:
                    tables.append(existing)
            else:
                st = SourceTable(
                    dataset_id=dataset.id,
                    table_name=table_name,
                    columns_json=json.dumps(columns),
                    mapping_json=json.dumps(mapping),
                    mapping_confirmed=False,
                    row_count=len(rows),
                )
                db.add(st)
                tables.append(st)
    db.commit()
    return tables


def run_ingestion(db: Session, dataset_id: int, job_id: int, auto_confirm: bool = False):
    job = db.get(ProcessingJob, job_id)
    dataset = db.get(Dataset, dataset_id)
    if not job or not dataset:
        return
    started = time.time()
    try:
        dataset.status = "inspecting"
        set_job(db, job, "inspecting", 8, "Inspecting uploaded files and discovering tables")
        inspect_dataset(db, dataset)
        db.refresh(dataset)

        set_job(db, job, "field_mapping", 18, "Suggesting canonical field mappings")
        tables = db.query(SourceTable).filter(SourceTable.dataset_id == dataset.id).all()
        if auto_confirm:
            for t in tables:
                t.mapping_confirmed = True
            db.commit()

        unconfirmed = [t for t in tables if not t.mapping_confirmed]
        if unconfirmed:
            dataset.status = "field_mapping"
            set_job(
                db,
                job,
                "field_mapping",
                20,
                "Waiting for user to review and confirm field mappings",
            )
            return

        set_job(db, job, "cleaning", 30, "Normalizing identifiers and cleaning records")
        dataset.status = "cleaning"

        total_rows = sum(t.row_count for t in tables)
        job.records_total = total_rows
        db.commit()

        processed = 0
        matches = 0
        new_entities = 0
        duplicates = 0

        for t in tables:
            mapping = json.loads(t.mapping_json or "{}")
            reverse = mapping
            for f in dataset.files:
                path = Path(f.filename)
                if not path.exists():
                    continue
                parsed = load_file(path)
                for table_name, columns, rows in parsed:
                    if table_name != t.table_name:
                        continue
                    set_job(
                        db,
                        job,
                        "indexing",
                        40 + (processed / max(total_rows, 1)) * 25,
                        f"Indexing {table_name} in batches of {settings.batch_size}",
                        records_total=total_rows,
                        records_processed=processed,
                    )
                    for chunk in iter_chunks(rows, settings.batch_size):
                        for row in chunk:
                            row_id = f"{Path(f.filename).stem}:{row.get('_row_id') or processed + 1}"
                            existing = (
                                db.query(SourceRecord)
                                .filter(
                                    SourceRecord.dataset_id == dataset.id,
                                    SourceRecord.table_name == table_name,
                                    SourceRecord.row_id == row_id,
                                )
                                .first()
                            )
                            email_src = _mapped(row, reverse, "email")
                            phone_src = _mapped(row, reverse, "phone")
                            user_src = _mapped(row, reverse, "username")
                            name_src = _mapped(row, reverse, "name")
                            member_src = _mapped(row, reverse, "member_id")
                            payload = {k: v for k, v in row.items() if k != "_row_id"}
                            if existing:
                                rec = existing
                                rec.raw_json = json.dumps(payload, ensure_ascii=False)
                                rec.email_norm = normalize_email(email_src)
                                rec.phone_norm = normalize_phone(phone_src)
                                rec.username_norm = normalize_username(user_src)
                                rec.name_norm = normalize_name(name_src)
                                rec.member_id_norm = normalize_member_id(member_src)
                            else:
                                rec = SourceRecord(
                                    dataset_id=dataset.id,
                                    table_name=table_name,
                                    row_id=row_id,
                                    raw_json=json.dumps(payload, ensure_ascii=False),
                                    email_norm=normalize_email(email_src),
                                    phone_norm=normalize_phone(phone_src),
                                    username_norm=normalize_username(user_src),
                                    name_norm=normalize_name(name_src),
                                    member_id_norm=normalize_member_id(member_src),
                                )
                                db.add(rec)
                            processed += 1
                        db.flush()

        set_job(db, job, "matching", 70, "Running hierarchical matching against master repository")
        dataset.status = "matching"
        records = db.query(SourceRecord).filter(SourceRecord.dataset_id == dataset.id).all()
        table_maps = {t.table_name: json.loads(t.mapping_json or "{}") for t in tables}
        for i, rec in enumerate(records):
            if rec.master_entity_id:
                continue
            mapping = table_maps.get(rec.table_name, {})
            _, is_new, is_dup = create_or_update_entity(db, rec, dataset, mapping)
            if is_new:
                new_entities += 1
            if is_dup:
                duplicates += 1
                matches += 1
            if i % 200 == 0:
                job.records_processed = i
                job.matches_found = matches
                job.new_entities = new_entities
                job.duplicates_caught = duplicates
                job.progress = 70 + (i / max(len(records), 1)) * 20
                db.commit()

        set_job(db, job, "enriching", 92, "Enriching master entities with source attribution")
        dataset.status = "enriching"
        dataset.record_count = processed
        db.commit()

        elapsed = round(time.time() - started, 2)
        dataset.status = "completed"
        set_job(
            db,
            job,
            "completed",
            100,
            f"Completed in {elapsed}s",
            records_processed=processed,
            records_total=total_rows,
            matches_found=matches,
            new_entities=new_entities,
            duplicates_caught=duplicates,
        )
    except Exception as exc:
        dataset.status = "failed"
        job.stage = "failed"
        job.error = str(exc)
        job.message = f"Pipeline failed: {exc}"
        job.finished_at = _utcnow()
        db.commit()


def _mapped(row: dict, mapping: dict, canonical: str) -> str:
    for src, dst in mapping.items():
        if dst == canonical:
            return str(row.get(src, "") or "")
    return str(row.get(canonical, "") or "")
