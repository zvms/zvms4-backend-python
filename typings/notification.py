from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    pin = "pin"
    important = "important"
    normal = "normal"


class Notification(BaseModel):
    id: str = Field(..., alias="_id")
    global_: bool = Field(..., alias="global")
    title: str
    content: str
    time: str
    publisher: str
    receivers: Optional[list[str]]
    route: Optional[str]
    anoymous: bool
    expire: str  # ISO 8601
    type: NotificationType
