from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import SAMPLE_DIR, settings
from app.database import Base, SessionLocal, engine
from app.routers import datasets, search, stats
from app.services.seed import generate_samples


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    generate_samples()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Multi-database entity resolution and unified data repository",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(search.router)
app.include_router(stats.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/samples")
def list_samples():
    files = []
    if SAMPLE_DIR.exists():
        for p in sorted(SAMPLE_DIR.iterdir()):
            if p.is_file():
                files.append({"name": p.name, "size": p.stat().st_size, "path": f"/api/samples/{p.name}"})
    return {"files": files}


@app.get("/api/samples/{name}")
def download_sample(name: str):
    path = SAMPLE_DIR / name
    if not path.exists() or not path.is_file():
        from fastapi import HTTPException

        raise HTTPException(404, "Sample not found")
    return FileResponse(path, filename=name)


@app.post("/api/bootstrap")
def bootstrap():
    from app.models import Dataset, DatasetFile, ProcessingJob
    from app.services.parser import sniff_type
    from app.services.pipeline import run_ingestion
    import shutil

    generate_samples()
    db = SessionLocal()
    created = []
    try:
        specs = [
            ("CRM Source A", "database_a", "database_a_crm.csv", "Customer CRM extract"),
            ("Billing Source B", "database_b", "database_b_billing.csv", "Billing address extract"),
            ("Directory Source C", "database_c", "database_c_directory.csv", "Internal staff directory"),
            ("Members Source D", "database_d", "database_d_members.sql", "Membership SQL dump"),
        ]
        from app.config import UPLOAD_DIR

        for name, tag, filename, desc in specs:
            existing = db.query(Dataset).filter(Dataset.source_tag == tag).first()
            if existing and existing.status == "completed":
                created.append({"id": existing.id, "name": existing.name, "skipped": True})
                continue
            ds = existing or Dataset(name=name, source_tag=tag, description=desc, status="uploaded")
            if not existing:
                db.add(ds)
                db.flush()
            src = SAMPLE_DIR / filename
            dest_dir = UPLOAD_DIR / f"dataset_{ds.id}"
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / filename
            shutil.copy2(src, dest)
            if not ds.files:
                db.add(
                    DatasetFile(
                        dataset_id=ds.id,
                        filename=str(dest),
                        original_name=filename,
                        part_name=Path(filename).stem,
                        file_type=sniff_type(filename),
                        size_bytes=dest.stat().st_size,
                    )
                )
            job = ProcessingJob(dataset_id=ds.id, stage="queued", progress=0, message="Bootstrap seed")
            db.add(job)
            db.commit()
            db.refresh(job)
            run_ingestion(db, ds.id, job.id, auto_confirm=True)
            created.append({"id": ds.id, "name": ds.name, "skipped": False})
        return {"ok": True, "datasets": created}
    finally:
        db.close()


frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
