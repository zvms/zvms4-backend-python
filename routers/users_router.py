import time
from fastapi import UploadFile
from fastapi import APIRouter, HTTPException, Depends, Form, Request
from typing import List
from fastapi.responses import StreamingResponse

from pydantic import BaseModel
from util import image_process, image_storage
from util.calculate import calculate_time
from util.cases import kebab_case_to_camel_case
from utils import (
    compulsory_temporary_token,
    get_current_user,
    timestamp_change,
    validate_object_id,
    get_img_token,
    randomString,
)
from datetime import datetime, timedelta
from jose import JWTError, jwt
from database import db
from bson import ObjectId
import settings
from util.cert import get_hashed_password_by_cert, validate_by_cert
import os
import config

router = APIRouter()


class AuthUser(BaseModel):
    id: str
    mode: str
    credential: str


@router.post("/auth")
async def auth_user(auth: AuthUser):
    id = auth.id
    mode = auth.mode
    credential = auth.credential

    if mode is None:
        mode = "long"

    result = await validate_by_cert(id, credential, mode)

    return {
        "token": result,
        "_id": id,
    }


class PutPassword(BaseModel):
    credential: str


@router.put("/{user_oid}/password")
async def change_password(
    user_oid: str, credential: PutPassword, user=Depends(compulsory_temporary_token)
):
    print(user)
    # Validate user's permission
    if "admin" not in user["per"] and user["id"] != user_oid:
        raise HTTPException(status_code=403, detail="Permission denied")

    password = await get_hashed_password_by_cert(credential.credential)

    # Change user's password
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user_oid)}, {"$set": {"password": str(password)}}
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.get("")
async def read_users(query: str):
    """
    Query users
    """
    result = (
        await db.zvms["users"]
        .find(
            {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"id": {"$regex": query, "$options": "i"}},
                ]
            },
            {
                "name": True,
                "id": True,
                "group": True,
            },
        )
        .sort({"id": 1})
        .to_list(5)
    )

    for user in result:
        user["_id"] = str(user["_id"])

    return {"status": "ok", "code": 200, "data": result}


@router.get("/{user_oid}")
async def read_user(user_oid: str):
    """
    Return user's information
    """
    # # 验证用户权限, 仅管理员可查看他人信息
    # if user["permission"] < 16 and user["_id"] != validate_object_id(user_oid):
    #     raise HTTPException(status_code=403, detail="Permission denied")

    # Read user's information
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})

    user["_id"] = str(user["_id"])
    del user["password"]
    return {
        "status": "ok",
        "code": 200,
        "data": user,
    }


@router.post("/{user_oid}/group")
async def add_user_to_group(
    user_oid: str, group_id: str, user=Depends(get_current_user)
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Add user to group
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user_oid)},
        {"$addToSet": {"group": validate_object_id(group_id)}},
    )


@router.delete("/{user_oid}/group/{group_id}")
async def remove_user_from_group(
    user_oid: str, group_id: str, user=Depends(get_current_user)
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Remove user from group
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user_oid)},
        {"$pull": {"group": validate_object_id(group_id)}},
    )


@router.get("/{user_oid}/activity")
async def read_user_activity(
    user_oid: str,
    registration: bool = False,  # 是否返回报名的义工, parameters
    user=Depends(get_current_user),
    page: int = -1,
    perpage: int = 10,
    query: str = "",
):
    """
    Return user's activities
    """
    # Check user's permission

    if "admin" not in user["per"] and user["id"] != str(validate_object_id(user_oid)):
        raise HTTPException(status_code=403, detail="Permission denied")

    count = await db.zvms.activities.count_documents(
        {"members._id": str(validate_object_id(user_oid))},
        # {"name": {"$regex": query, "$options": "i"}},
    )
    # Read user's activities
    all_activities = (
        await db.zvms.activities.find(
            {
                "members._id": str(validate_object_id(user_oid)),
                "name": {"$regex": query, "$options": "i"},
            },
            {
                "name": 1,
                "date": 1,
                "_id": 1,
                "status": 1,
                "type": 1,
                "special": 1,
                "members.$": 1,
            },
        )
        .skip(0 if page == -1 else (page - 1) * perpage)
        .limit(0 if page == -1 else perpage)
        .to_list(None if page == -1 else perpage)
    )

    for activity in all_activities:
        activity["_id"] = str(activity["_id"])

    return {
        "status": "ok",
        "code": 200,
        "data": all_activities,
        "metadata": {
            "size": count,
        },
    }


@router.get("/{user_oid}/time")
async def read_user_time(user_oid: str, user=Depends(get_current_user)):
    """
    Return user's time
    """
    # Check user's permission
    if (
        "admin" not in user["per"]
        and "department" not in user["per"]
        and user["id"] != str(validate_object_id(user_oid))
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await calculate_time(user_oid)
    return {
        "status": "ok",
        "code": 200,
        "data": {
            "onCampus": result["on-campus"],
            "offCampus": result["off-campus"],
            "socialPractice": result["social-practice"],
            "trophy": result["trophy"],
            "total": result["total"],
        },
    }


@router.get("/{user_oid}/notification")
async def read_notifications(
    user_oid: str, page: int = 1, perpage: int = 10, user=Depends(get_current_user)
):
    """
    Get Notifications
    """
    # Get notification list
    count = await db.zvms.notifications.count_documents(
        {
            "$or": [
                {"receivers": str(user_oid)},
                {"global": True},
            ]
        }
    )
    notifications = (
        await db.zvms.notifications.find(
            {
                "$or": [
                    {"receivers": str(user_oid)},
                    {"global": True},
                ]
            }
        )
        .sort("_id", -1)
        .skip(0 if page == -1 else (page - 1) * perpage)
        .limit(0 if page == -1 else perpage)
        .to_list(None if page == -1 else perpage)
    )

    if user_oid != user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    for notification in notifications:
        notification["_id"] = str(notification["_id"])
    return {
        "status": "ok",
        "code": 200,
        "data": notifications,
        "metadata": {
            "size": count,
        },
    }


@router.get("/{user_oid}/image")
async def read_images(
    user_oid: str,
    user=Depends(get_current_user),
    page: int = 1,
    perpage: int = 10,
):
    if user["id"] != user_oid and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    user = (
        await db.zvms.images.find(
            {
                "uploader": user_oid,
            }
        )
        .skip(0 if page == -1 else (page - 1) * perpage)
        .limit(0 if page == -1 else perpage)
        .to_list(None if page == -1 else perpage)
    )
    return {
        "status": "ok",
        "code": 200,
        "data": user["images"],
    }
