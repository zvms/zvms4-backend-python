from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from h11 import Data
from urllib.parse import urlencode, urlparse

from conversion.groups import trans_permissions
from typings.user import User, UserPosition as UserPositionV1
from typings.user_v2 import UserPosition as UserPositionV2
import jwt
from typing import Optional
from datetime import datetime, timezone
from database import db
from bson import ObjectId
import settings
from util.cert import jwt_decode
import requests
import random
import string

# Secret key and algorithm for JWT
SECRET_KEY = open("aes_key.txt", "r").read()
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def validate_object_id(id: str):
    try:
        _id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Object ID")
    return _id


def string_to_option_object_id(id: str):
    try:
        _id = ObjectId(id)
    except:
        return None
    return _id


def upgrade_user_positions(positions: list[UserPositionV1]) -> list[UserPositionV2]:
    return [trans_permissions(pos) for pos in positions]


async def get_user(oid: str):
    """
    Get user by oid
    """
    user = await db.zvms.users.find_one({"_id": validate_object_id(oid)})
    if user:
        return user
    print(user)
    return None


async def compulsory_temporary_token(token: str = Depends(oauth2_scheme)):
    result = await get_current_user(token, "short", True)
    return result


async def optional_current_user(token: str = Depends(oauth2_scheme)):
    result = await get_current_user(token, "long", False)
    print(result)
    return result


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    scope: Optional[str] = "long",
    exception: bool = True,
):
    """
    Inject `Depends`, returning user info
    """

    def raise_exception():
        if exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            return None

    try:
        if token is None:
            raise_exception()
        # Decode JWT
        payload = jwt_decode(token)
        oid: str = payload.get("sub", None)
        exp: int = payload.get("exp", None)
        jti: str = payload.get("jti", None)

        # Check if the token is valid
        if oid is None or exp is None or jti is None:
            raise_exception()

        # Check if the token is expired
        if exp is not None and datetime.utcnow() >= datetime.fromtimestamp(exp):
            raise_exception()
        if scope == "short" and payload["scope"] == "access_token":
            raise_exception()
        user = {
            "id": oid,
            "perm": upgrade_user_positions(payload.get("per", None)),
            "per": upgrade_user_positions(payload.get("per", None)),
            "scope": payload.get("scope", None),
        }
        if user is None:
            raise_exception()
        return user
    except jwt.PyJWTError:
        raise_exception()


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


def get_img_token_url(user_oid: str, per: str):
    url = urlparse(settings.IMGBED_SERVER)
    url._replace(path="/user/getToken")
    query = urlencode(
        {
            "superAdminToken": settings.IMGBED_SECRET_KEY,
            "userId": user_oid,
            "permission": per,
        }
    )
    url._replace(query=query)
    return url.geturl()


def get_img_token(user_oid, per):
    url = get_img_token_url(user_oid, per)
    res = requests.get(url)
    return res.json()["token"]


def randomString(length=16):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )
