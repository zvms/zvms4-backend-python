from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from h11 import Data
from typings.user import User
import jwt
from typing import Optional
from datetime import datetime, timezone
from database import db
from bson import ObjectId
import settings
from util.cert import jwt_decode
import requests


# Secret key and algorithm for JWT
SECRET_KEY = open("aes_key.txt", "r").read()
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
    Get user by oid
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


async def compulsory_temporary_token(token: str = Depends(oauth2_scheme)):
    result = await get_current_user(token, 'short')
    return result

async def get_current_user(token: str = Depends(oauth2_scheme), scope: Optional[str] = 'long'):
    """
    用于 Depends 注入, 返回当前用户信息 User
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode JWT
        payload = jwt_decode(token)
        oid: str = payload.get("sub", None)
        exp: int = payload.get("exp", None)
        jti: str = payload.get("jti", None)

        # Check if the token is valid
        if oid is None or exp is None or jti is None:
            raise credentials_exception

        # Check if the token is expired
        if exp is not None and datetime.utcnow() >= datetime.fromtimestamp(exp):
            raise credentials_exception
        if scope == 'short' and payload['scope'] == 'access_token':
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = {
        "id": oid,
        "per": payload.get("per", None),
    }
    if user is None:
        raise credentials_exception
    return user


def timestamp_change(date_string: str):
    """
    Change ISO-8601 to timestamp
    """
    dt = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    # Change the time zone to UTC
    dt = dt.replace(tzinfo=timezone.utc)
    # Get the timestamp
    timestamp = dt.timestamp()
    # Return the timestamp
    return int(timestamp)

def get_img_token(user_oid, per):
    return requests.get(f"http://localhost:6666/user/getToken?superAdminToken={settings.IMGBED_SECRET_KEY}&userId={user_oid}&permission={per}").json()["data"]["token"]
