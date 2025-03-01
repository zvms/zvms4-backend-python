from datetime import datetime
from enum import Enum
from typing import Optional

from pandas import DataFrame
from pydantic import BaseModel, field_validator, ConfigDict


class ExportStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ExportFormat(Enum):
    csv = "csv"
    excel = "excel"
    json = "json"
    latex = "latex"
    html = "html"

    def suffix(self):
        if self == ExportFormat.excel:
            return "xlsx"
        elif self == ExportFormat.latex:
            return "tex"
        return self.value

    def mime(self):
        if self == ExportFormat.excel:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif self == ExportFormat.csv:
            return "text/csv"
        elif self == ExportFormat.json:
            return "application/json"
        elif self == ExportFormat.latex:
            return "application/x-latex"
        elif self == ExportFormat.html:
            return "text/html"


class ExportVariant(Enum):
    users = "users"
    activities = "activities"
    time = "time"
    groups = "groups"
    logs = "logs"


class ExportTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str # UUID
    status: ExportStatus
    format: ExportFormat
    variant: ExportVariant
    export_start: Optional[datetime]
    export_end: Optional[datetime]
    task_start: datetime
    task_end: Optional[datetime]
    percentage: float = 0
    errmsg: str = ''
    result: Optional[DataFrame]

    @field_validator("result", mode="before")
    def validate_dataframe(cls, value):
        if value is not None and not isinstance(value, DataFrame):
            raise ValueError("df must be a pandas DataFrame")
        return value
