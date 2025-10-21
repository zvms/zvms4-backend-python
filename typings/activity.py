from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
from util.user import get_user_name


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
    id: str = Field(..., alias="_id")
    status: MemberActivityStatus
    mode: ActivityMode
    duration: float

    async def log(self):
        return f"User {await get_user_name(self.id)} joined activity with mode {self.mode} and duration {self.duration}."


class Registration(BaseModel):
    place: Optional[str | None] = None


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
    special: Optional[Special | None] = None
    approver: str

    async def log(self, user: str = ""):
        template = f"""User {await get_user_name(user)} created activity {self.name} with description {self.description} at {self.createdAt} (ID: $PLACEHOLDER). It involves users:"""
        for member in self.members:
            template += await member.log() + "\n"
        return template
