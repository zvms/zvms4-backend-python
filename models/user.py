from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    _id: str                # 用户 UUID(数据库 oid)
    username: str           # 用户名(学号)
    password_hashed: str    # 密码(MD5)
    realname: str           # 真实姓名
    permission: int         # 权限等级

class TokenData(BaseModel):
    username: Optional[str] = None
