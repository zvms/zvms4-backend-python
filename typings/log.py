from fastapi import Request, Depends
from datetime import datetime
from typing import Optional

from database import db
from util.logify import binding_user_credentials
from util.object_id import get_current_user


class ZVMSLog:
    url: str
    user: str
    # Clarity ID, which is also Device ID
    clarity: str
    data: str
    timestamp: float
    ip: str
    xuehai: Optional[str | None]

    def __init__(
        self,
        url: str = "",
        user: str = "",
        clarity: str = "",
        data: str = "",
        ip: str = "",
        xuehai: Optional[str | None] = "",
        timestamp: float = datetime.now().timestamp(),
    ):
        self.url = url
        self.user = user
        self.clarity = clarity
        self.data = data
        self.timestamp = timestamp
        self.ip = ip
        self.xuehai = xuehai

    def model_dump(self) -> dict:
        return {
            "url": self.url,
            "user": self.user,
            "clarity": self.clarity,
            "data": self.data,
            "ip": self.ip,
            "xuehai": "" if self.xuehai is None else self.xuehai,
            "timestamp": self.timestamp,
        }

    def with_text(self, text: str) -> "ZVMSLog":
        self.data = text
        return self

    async def insert_log(self):
        return await db.zvms.logs.insert_one(self.model_dump())

    @property
    def includes_clarity(self) -> bool:
        return self.clarity != "" and self.clarity is not None

    @property
    def includes_xuehai(self) -> bool:
        return self.xuehai != "" and self.xuehai is not None


def inject_log(
    request: Request,
    user=Depends(get_current_user),
    meta=Depends(binding_user_credentials),
):
    url = str(request.url)
    user = user["id"]
    clarity = meta["clarity_id"]
    xuehai = meta["xuehai_id"]
    ip = meta["ip"]
    data = ""
    timestamp = datetime.timestamp(datetime.now())
    return ZVMSLog(url, user, clarity, data, ip, xuehai, timestamp)
