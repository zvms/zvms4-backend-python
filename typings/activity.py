from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from enum import Enum


class ActivityType(str, Enum):
    specified = "specified"
    special = "special"
    social = "social"
    scale = "scale"


class MemberActivityStatus(str, Enum):
    draft = "draft"
    pending = "pending"
    effective = "effective"
    refused = "refused"
    rejected = "rejected"


class ActivityMode(str, Enum):
    on_campus = "on-campus"
    off_campus = "off-campus"
    social_practice = "social-practice"


class ActivityMember(BaseModel):
    id: str = Field(..., alias='_id')
    status: MemberActivityStatus
    mode: ActivityMode
    duration: float


class ClassRegistration(BaseModel):
    classid: int
    max: int
    min: int | None = None


class Registration(BaseModel):
    deadline: str  # ISO 8601
    place: str
    duration: float
    classes: list[ClassRegistration]


class ActivityStatus(str, Enum):
    pending = "pending"
    effective = "effective"
    refused = "refused"


class SpecialActivityClassify(str, Enum):
    prize = "prize"
    import_ = "import"
    club = "club"
    other = "other"
    deduction = "deduction"


class Special(BaseModel):
    classify: SpecialActivityClassify
    prize: str | None = None
    origin: str | None = None
    reason: str | None = None


class Activity(BaseModel):
    _id: str
    type: ActivityType
    name: str
    description: str
    members: list[ActivityMember]
    registration: Optional[Registration | None] = None
    date: str  # ISO 8601
    createdAt: str  # ISO 8601
    updatedAt: str  # ISO 8601
    creator: str
    status: ActivityStatus
    url: Optional[str | None] = None
    special: Optional[Special | None] = None
