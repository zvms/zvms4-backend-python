from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum
from typings.user import UserPosition
from bson import ObjectId


class GroupType(str, Enum):
    class_ = "class"
    permission = "permission"
    group = "group"


class Group(BaseModel):
    _id: ObjectId | str
    name: str
    type: GroupType
    description: Optional[str]
    permissions: list[UserPosition]
    # Doesn't contain members, and it's not necessary to contain it in the model
