from enum import Enum
from bson import ObjectId
from pydantic import BaseModel, Field
from typings.activity import ActivityMode


class TrophyType(str, Enum):
    academic = "academic"
    art = "art"
    sports = "sports"
    others = "others"


class TrophyLevel(str, Enum):
    district = "district"
    city = "city"
    province = "province"
    national = "national"
    international = "international"


class TrophyAward(BaseModel):
    name: str
    duration: float


class TrophyStatus(str, Enum):
    pending = "pending"
    effective = "effective"
    refused = "refused"


class TrophyMemberStatus(str, Enum):
    pending = "pending"
    effective = "effective"
    refused = "refused"


class TrophyMember(BaseModel):
    id: str = Field(..., alias='_id')
    award: str
    mode: ActivityMode
    status: TrophyMemberStatus


class Trophy(BaseModel):
    _id: str
    name: str
    type: TrophyType
    level: TrophyLevel
    awards: list[TrophyAward]
    team: bool
    status: TrophyStatus
    members: list[TrophyMember]
    creator: str
    instructor: str
    deadline: str  # ISO 8601
    time: str  # ISO 8601
    createdAt: str  # ISO 8601
