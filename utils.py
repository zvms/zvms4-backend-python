from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from h11 import Data
from models.user import User
from jose import JWTError, jwt
from typing import Optional
from datetime import datetime, timezone
from database import db
from bson import ObjectId
import settings



# jwt 相关配置
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def validate_object_id(id: str):
    try:
        _id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Object ID")
    return _id


async def get_user(oid: str):
    """
    给定用户 $OID, 返回用户信息 User
    """
    user = await db.zvms.users.find_one({"_id": validate_object_id(oid)})
    if user:
        return user
    print(user)
    return None


async def authenticate_user(oid: str, password: str):
    """
    给定用户名和密码 (MD5), 验证用户身份
    """
    user = await get_user(oid)
    if not user:
        return None
    if user['password_hashed'] != password:
        return None
    print(user)
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    用于 Depends 注入, 返回当前用户信息 User
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 解码 JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        oid: str = payload.get("id", None)
        password: str = payload.get("password", None)
        exp: int = payload.get("exp", None)

        # 验证 JWT 是否完整
        if oid is None or password is None or exp is None:
            raise credentials_exception
        
        # 验证 JWT 是否过期
        if exp is not None and datetime.utcnow() >= datetime.fromtimestamp(exp):
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = authenticate_user(oid=oid, password=password)
    if user is None:
        raise credentials_exception
    return await user


async def timestamp_change(date_string: str):
    """
    时间戳转换
    """
    dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    # 将 datetime 对象转换为 UTC
    dt = dt.replace(tzinfo=timezone.utc)
    # 将 datetime 对象转换为时间戳
    timestamp = dt.timestamp()
    # 返回时间戳 int
    return int(timestamp)