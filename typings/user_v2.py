from pydantic import BaseModel, Field
from typing import List, Literal


class User(BaseModel):
    _id: str  # ObjectId as string
    id: str
    number: str
    groups: List[str]
    past: List[str]


UserPosition = Literal["admin", "volunteer", "club", "monitor", "student"]


class WithPassword(User):
    password: str


class UserLogin(WithPassword):
    id: int


class UserActivityTimeSums(BaseModel):
    onCampus: float
    offCampus: float
    socialPractice: float
