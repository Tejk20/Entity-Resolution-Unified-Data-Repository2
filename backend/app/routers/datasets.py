import json
import shutil
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import SessionLocal, get_db
from app.models import Dataset, DatasetFile, ProcessingJob, SourceTable
from app.schemas import DatasetCreate, DatasetOut, FileOut, MappingUpdate, TableMapping
from app.services.mapper import suggest_mapping
from app.services.parser import sniff_type
from app.services.pipeline import inspect_dataset, run_ingestion

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _file_count(ds: Dataset) -> int:
    return len(ds.files or [])


def _table_count(ds: Dataset) -> int:
    return len(ds.tables or [])


def serialize_dataset(ds: Dataset) -> DatasetOut:
    return DatasetOut(
        id=ds.id,
        name=ds.name,
        source_tag=ds.source_tag,
        description=ds.description or "",
        status=ds.status,
        record_count=ds.record_count or 0,
        created_at=ds.created_at,
        updated_at=ds.updated_at,
        file_count=_file_count(ds),
        table_count=_table_count(ds),
    )


def _run_job(dataset_id: int, job_id: int, auto_confirm: bool):
    db = SessionLocal()
    try:
        run_ingestion(db, dataset_id, job_id, auto_confirm=auto_confirm)
    finally:
        db.close()


@router.get("", response_model=list[DatasetOut])
def list_datasets(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).order_by(Dataset.id.desc()).all()
    return [serialize_dataset(d) for d in datasets]


@router.post("", response_model=DatasetOut)
def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)):
    ds = Dataset(
        name=payload.name,
        source_tag=payload.source_tag,
        description=payload.description,
        status="created",
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return serialize_dataset(ds)


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    return serialize_dataset(ds)


@router.post("/{dataset_id}/upload", response_model=list[FileOut])
async def upload_files(
    dataset_id: int,
    files: list[UploadFile] = File(...),
    part_name: str = Form(""),
    db: Session = Depends(get_db),
):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    saved = []
    dest_dir = UPLOAD_DIR / f"dataset_{ds.id}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for upload in files:
        original = upload.filename or "upload.bin"
        kind = sniff_type(original)
        if kind == "unknown":
            raise HTTPException(400, f"Unsupported file type: {original}. Use .csv or .sql")
        dest = dest_dir / original
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{dest.stem}_{counter}{dest.suffix}"
            counter += 1
        with dest.open("wb") as fh:
            shutil.copyfileobj(upload.file, fh)
        rec = DatasetFile(
            dataset_id=ds.id,
            filename=str(dest),
            original_name=original,
            part_name=part_name or dest.stem,
            file_type=kind,
            size_bytes=dest.stat().st_size,
        )
        db.add(rec)
        saved.append(rec)
    ds.status = "uploaded"
    db.commit()
    for rec in saved:
        db.refresh(rec)
    return saved


@router.get("/{dataset_id}/files", response_model=list[FileOut])
def list_files(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    return ds.files


@router.post("/{dataset_id}/inspect")
def inspect(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    if not ds.files:
        raise HTTPException(400, "Upload files before inspecting")
    ds.status = "inspecting"
    db.commit()
    tables = inspect_dataset(db, ds)
    ds.status = "field_mapping"
    db.commit()
    return {"ok": True, "tables": len(tables)}


@router.get("/{dataset_id}/mappings", response_model=list[TableMapping])
def get_mappings(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    result = []
    for t in ds.tables:
        columns = json.loads(t.columns_json or "[]")
        mapping = json.loads(t.mapping_json or "{}")
        suggestions = suggest_mapping(columns)
        result.append(
            TableMapping(
                table_id=t.id,
                table_name=t.table_name,
                columns=columns,
                mapping=mapping,
                suggestions=suggestions,
                mapping_confirmed=t.mapping_confirmed,
                row_count=t.row_count,
            )
        )
    return result


@router.put("/{dataset_id}/tables/{table_id}/mapping")
def update_mapping(
    dataset_id: int,
    table_id: int,
    payload: MappingUpdate,
    db: Session = Depends(get_db),
):
    table = db.get(SourceTable, table_id)
    if not table or table.dataset_id != dataset_id:
        raise HTTPException(404, "Table not found")
    table.mapping_json = json.dumps(payload.mapping)
    table.mapping_confirmed = True
    db.commit()
    return {"ok": True}


@router.post("/{dataset_id}/confirm-mappings")
def confirm_all(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    for t in ds.tables:
        t.mapping_confirmed = True
    db.commit()
    return {"ok": True}


@router.post("/{dataset_id}/process")
def process_dataset(
    dataset_id: int,
    auto_confirm: bool = False,
    db: Session = Depends(get_db),
):
    ds = db.get(Dataset, dataset_id)
    if not ds:
        raise HTTPException(404, "Dataset not found")
    job = ProcessingJob(
        dataset_id=ds.id,
        stage="queued",
        progress=0,
        message="Queued for batch ingestion",
    )
    db.add(job)
    ds.status = "queued"
    db.commit()
    db.refresh(job)
    thread = threading.Thread(target=_run_job, args=(ds.id, job.id, auto_confirm), daemon=True)
    thread.start()
    return {"job_id": job.id, "dataset_id": ds.id, "stage": job.stage}
