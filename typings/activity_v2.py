from datetime import datetime
from pydantic import BaseModel
from typing import Literal


class Activity(BaseModel):
    _id: str
    type: Literal["on-campus", "off-campus", "social-practice", "hybrid"]
    name: str
    description: str
    date: datetime  # ISO 8601
    createdAt: datetime  # ISO 8601
    updatedAt: datetime  # ISO 8601
    appointee: str  # ID of the responsible user
    approver: str  # ID or literal "authority" | "member"
    creator: str
    status: Literal["pending", "effective", "refused"]
    place: str
    origin: Literal[
        "labor",
        "organization",
        "tasks",
        "occasions",
        "import",
        "activities",
        "practice",
        "club",
        "prize",
        "other",
    ]


class ActivityMember(BaseModel):
    _id: str
    member: str
    activity: str
    status: Literal["effective", "refused", "pending"]
    mode: Literal["on-campus", "off-campus", "social-practice"]
    duration: float
