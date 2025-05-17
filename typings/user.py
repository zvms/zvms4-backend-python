from dataclasses import field
from enum import Enum
from pydantic import BaseModel

from util.user import get_user_name


class UserSex(str, Enum):
    male = "male"
    female = "female"
    unknown = "unknown"


class UserPosition(str, Enum):
    student = "student"
    secretary = "secretary"
    department = "department"
    admin = "admin"


class UserLogin(BaseModel):
    id: str
    credential: str


class UserEligibility(Enum):
    Rating = "rating"


class User(BaseModel):
    _id: str
    id: str
    name: str
    sex: UserSex
    group: list[str]
    past: list[str]
    eligibility: list[UserEligibility] = field(default_factory=list)


class UserActivityTimeSums(BaseModel):
    onCampus: float
    offCampus: float
    socialPractice: float
    trophy: float
