from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    name: str
    source_tag: str
    description: str = ""


class DatasetOut(BaseModel):
    id: int
    name: str
    source_tag: str
    description: str = ""
    status: str
    record_count: int
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    table_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class FileOut(BaseModel):
    id: int
    filename: str
    original_name: str
    part_name: str = ""
    file_type: str
    size_bytes: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MappingSuggestion(BaseModel):
    source_column: str
    canonical_field: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""


class TableMapping(BaseModel):
    table_id: int
    table_name: str
    columns: list[str]
    mapping: dict[str, str]
    suggestions: list[MappingSuggestion] = []
    mapping_confirmed: bool = False
    row_count: int = 0


class MappingUpdate(BaseModel):
    mapping: dict[str, str]


class JobOut(BaseModel):
    id: int
    dataset_id: Optional[int] = None
    stage: str
    progress: float
    message: str = ""
    records_processed: int = 0
    records_total: int = 0
    matches_found: int = 0
    new_entities: int = 0
    duplicates_caught: int = 0
    started_at: datetime
    finished_at: Optional[datetime] = None
    error: str = ""

    model_config = ConfigDict(from_attributes=True)


class FieldAttribution(BaseModel):
    field_name: str
    original_value: str
    normalized_value: str
    source_db: str
    source_table: str
    row_id: str
    timestamp: datetime
    is_primary: bool = False


class EntityCard(BaseModel):
    id: int
    status: str
    display_name: str
    match_count: int
    source_count: int
    created_at: datetime
    updated_at: datetime
    identifiers: dict[str, list[str]] = Field(default_factory=dict)
    fields: list[FieldAttribution] = Field(default_factory=list)
    linked_sources: list[dict[str, Any]] = Field(default_factory=list)
    merged: dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: str
    identifier_type: Optional[str] = None


class SearchStep(BaseModel):
    hop: int
    identifier_type: str
    identifier_value: str
    records_found: int
    new_identifiers: list[dict[str, str]] = Field(default_factory=list)


class SearchResult(BaseModel):
    query: str
    hops: list[SearchStep]
    entity: Optional[EntityCard] = None
    records_visited: int = 0
    datasets_touched: list[str] = Field(default_factory=list)


class StatsOut(BaseModel):
    total_records: int = 0
    total_sources: int = 0
    total_datasets: int = 0
    matched_entities: int = 0
    unmatched_entities: int = 0
    total_entities: int = 0
    duplicates_caught: int = 0
    jobs_completed: int = 0
    avg_processing_seconds: float = 0.0
    last_job_seconds: float = 0.0
    pipeline_stages: list[dict[str, Any]] = Field(default_factory=list)
