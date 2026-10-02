from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Dataset, MasterEntity, ProcessingJob, SourceRecord
from app.schemas import JobOut, StatsOut
from app.services.pipeline import STAGES

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total_records = db.query(func.count(SourceRecord.id)).scalar() or 0
    total_datasets = db.query(func.count(Dataset.id)).scalar() or 0
    total_sources = (
        db.query(func.count(func.distinct(Dataset.source_tag))).scalar() or 0
    )
    total_entities = db.query(func.count(MasterEntity.id)).scalar() or 0
    matched_entities = (
        db.query(func.count(MasterEntity.id)).filter(MasterEntity.status == "matched").scalar() or 0
    )
    unmatched_entities = (
        db.query(func.count(MasterEntity.id)).filter(MasterEntity.status == "unmatched").scalar() or 0
    )
    jobs = db.query(ProcessingJob).all()
    completed = [j for j in jobs if j.stage == "completed" and j.finished_at and j.started_at]
    duplicates = sum(j.duplicates_caught or 0 for j in jobs)
    durations = []
    for j in completed:
        durations.append((j.finished_at - j.started_at).total_seconds())
    avg = sum(durations) / len(durations) if durations else 0.0
    last = durations[-1] if durations else 0.0

    stage_counts = []
    for stage in STAGES:
        count = db.query(func.count(Dataset.id)).filter(Dataset.status == stage).scalar() or 0
        stage_counts.append({"stage": stage, "count": count})

    return StatsOut(
        total_records=total_records,
        total_sources=total_sources,
        total_datasets=total_datasets,
        matched_entities=matched_entities,
        unmatched_entities=unmatched_entities,
        total_entities=total_entities,
        duplicates_caught=duplicates,
        jobs_completed=len(completed),
        avg_processing_seconds=round(avg, 2),
        last_job_seconds=round(last, 2),
        pipeline_stages=stage_counts,
    )


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(dataset_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(ProcessingJob).order_by(ProcessingJob.id.desc())
    if dataset_id:
        q = q.filter(ProcessingJob.dataset_id == dataset_id)
    return q.limit(50).all()


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        from fastapi import HTTPException

        raise HTTPException(404, "Job not found")
    return job
