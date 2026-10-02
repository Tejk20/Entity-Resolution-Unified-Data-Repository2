from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from pathlib import Path

from app.config import settings, DATA_DIR, BASE_DIR

connect_args = {}
database_url = settings.database_url
if database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw = database_url.replace("sqlite:///", "", 1)
    if raw and not raw.startswith("/"):
        db_path = (BASE_DIR / raw.lstrip("./")).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{db_path}"

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
