from fastapi import Request
from enum import Enum
from json import dumps
from database import db


def get_client_ip(request: Request) -> str:
    """
    Get client IP address
    """
    if "X-Forwarded-For" in request.headers:
        return request.headers["X-Forwarded-For"]
    return request.client.host


class LogType(Enum):
    CreateActivity = "CA"
    UpdateActivityTitle = "UAT"
    UpdateActivityDescription = "UAD"
    AddActivityMember = "AAM"
    RemoveActivityMember = "RAM"
    ChangeActivityStatus = "CAS"
    ChangeMemberStatus = "CMS"
    ModifyUserPassword = "MUP"
    ModifyUserData = "MUD"
    CreateGroup = "CG"
    UpdateGroupName = "UGN"
    UpdateGroupDescription = "UGD"
    AddGroupMember = "AGM"
    RemoveGroupMember = "RGM"
    CreateNotification = "CN"
    UpdateNotification = "UN"
    DeleteNotification = "DN"

    def __str__(self):
        return self.value


class ZVMSLog:
    def __init__(
        self, log_type: LogType, user: str, detail: str, ip: str, affected: list[str]
    ):
        self.type = log_type
        self.user = user
        self.detail = detail
        self.ip = ip
        self.affected = affected

    def __str__(self):
        return dumps(
            {
                "type": self.type.value,
                "user": str(self.user),
                "detail": self.detail,
                "ip": self.ip,
                "affected": self.affected,
            }
        )

    def model_dump(self) -> dict:
        return {
            "type": self.type.value,
            "user": self.user,
            "detail": self.detail,
            "ip": self.ip,
            "affected": self.affected,
        }

    def save(self):
        db.zvms.logs.insert_one(self.model_dump())
