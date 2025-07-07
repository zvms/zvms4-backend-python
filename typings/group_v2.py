from pydantic import BaseModel
from typing import Literal, List
from typings.user_v2 import UserPosition


class Group(BaseModel):
    _id: str
    name: str
    type: Literal["class", "organization"]
    description: str
    charge: str  # ID of the person in charge
    contact: str  # ID of person to contact
    permissions: List[UserPosition]
    categories: List[str]


class Category(BaseModel):
    _id: str
    type: Literal["grade", "class", "organization"]
    name: str
    description: str
