from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel


class ExportStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ExportFormat(str, Enum):
    json = "json"
    csv = "csv"
    xlsx = "xlsx"


class Export(BaseModel):
    collection: str  # `time`, `trophies`, `activities`, `notifications`, `users`, `groups`, etc.
    format: ExportFormat  # `json`, `csv`, `xlsx`, etc.
    start: str  # ISO 8601 date
    end: str  # ISO 8601 date
    filters: Optional[dict[str, str]]  # { "key": "value" }
    sort: str
    limit: int
    offset: int


class ExportResponse(BaseModel):
    id: str
    status: ExportStatus
    url: Optional[str]
    data: Any
    format: ExportFormat
    error: Optional[str]
