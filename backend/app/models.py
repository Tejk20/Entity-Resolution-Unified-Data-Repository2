from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Float,
    Index,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    source_tag = Column(String(255), nullable=False, index=True)
    description = Column(Text, default="")
    status = Column(String(64), default="uploaded", index=True)
    record_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    files = relationship("DatasetFile", back_populates="dataset", cascade="all, delete-orphan")
    tables = relationship("SourceTable", back_populates="dataset", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="dataset", cascade="all, delete-orphan")


class DatasetFile(Base):
    __tablename__ = "dataset_files"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    original_name = Column(String(512), nullable=False)
    part_name = Column(String(128), default="")
    file_type = Column(String(32), nullable=False)
    size_bytes = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=utcnow)

    dataset = relationship("Dataset", back_populates="files")


class SourceTable(Base):
    __tablename__ = "source_tables"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    table_name = Column(String(255), nullable=False)
    columns_json = Column(Text, default="[]")
    mapping_json = Column(Text, default="{}")
    mapping_confirmed = Column(Boolean, default=False)
    row_count = Column(Integer, default=0)

    dataset = relationship("Dataset", back_populates="tables")


class SourceRecord(Base):
    __tablename__ = "source_records"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    table_name = Column(String(255), nullable=False, index=True)
    row_id = Column(String(128), nullable=False)
    raw_json = Column(Text, default="{}")
    email_norm = Column(String(320), index=True)
    phone_norm = Column(String(32), index=True)
    username_norm = Column(String(255), index=True)
    name_norm = Column(String(512), index=True)
    member_id_norm = Column(String(128), index=True)
    master_entity_id = Column(Integer, ForeignKey("master_entities.id"), index=True)
    ingested_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_source_email", "email_norm"),
        Index("ix_source_phone", "phone_norm"),
        Index("ix_source_username", "username_norm"),
        Index("ix_source_member", "member_id_norm"),
        UniqueConstraint("dataset_id", "table_name", "row_id", name="uq_source_row"),
    )


class MasterEntity(Base):
    __tablename__ = "master_entities"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(32), default="unmatched", index=True)
    match_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)
    display_name = Column(String(512), default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    fields = relationship("EntityField", back_populates="entity", cascade="all, delete-orphan")
    identifiers = relationship("IdentifierIndex", back_populates="entity", cascade="all, delete-orphan")


class EntityField(Base):
    __tablename__ = "entity_fields"

    id = Column(Integer, primary_key=True)
    master_entity_id = Column(Integer, ForeignKey("master_entities.id"), nullable=False, index=True)
    field_name = Column(String(128), nullable=False, index=True)
    original_value = Column(Text, default="")
    normalized_value = Column(String(512), default="", index=True)
    source_db = Column(String(255), default="")
    source_table = Column(String(255), default="")
    row_id = Column(String(128), default="")
    timestamp = Column(DateTime, default=utcnow)
    is_primary = Column(Boolean, default=False)

    entity = relationship("MasterEntity", back_populates="fields")


class IdentifierIndex(Base):
    __tablename__ = "identifier_index"

    id = Column(Integer, primary_key=True)
    identifier_type = Column(String(64), nullable=False)
    normalized_value = Column(String(512), nullable=False)
    master_entity_id = Column(Integer, ForeignKey("master_entities.id"), nullable=False, index=True)
    source_record_id = Column(Integer, ForeignKey("source_records.id"), index=True)

    entity = relationship("MasterEntity", back_populates="identifiers")

    __table_args__ = (
        Index("ix_ident_type_value", "identifier_type", "normalized_value"),
        UniqueConstraint(
            "identifier_type",
            "normalized_value",
            "master_entity_id",
            name="uq_ident_entity",
        ),
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True, index=True)
    stage = Column(String(64), default="queued", index=True)
    progress = Column(Float, default=0.0)
    message = Column(Text, default="")
    records_processed = Column(Integer, default=0)
    records_total = Column(Integer, default=0)
    matches_found = Column(Integer, default=0)
    new_entities = Column(Integer, default=0)
    duplicates_caught = Column(Integer, default=0)
    started_at = Column(DateTime, default=utcnow)
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, default="")

    dataset = relationship("Dataset", back_populates="jobs")


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False)
    value = Column(String(255), default="0")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
