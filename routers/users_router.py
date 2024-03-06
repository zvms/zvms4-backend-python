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
    返回用户列表
    """
    # 读取用户列表
    result = await db.zvms["users"].find().to_list(3000)

    query_result = []

    for user in result:
        if query in user["name"] or query in str(user["id"]):
            user["_id"] = str(user["_id"])
            user["password"] = ""
            query_result.append(user)

    # 返回用户列表, 排除密码
    return {"status": "ok", "code": 200, "data": query_result}


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
):
    """
    Return user's activities
    """
    # Check user's permission

    if "admin" not in user["per"] and user["id"] != str(validate_object_id(user_oid)):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Read user's activities
    all_activities = await db.zvms.activities.find(
        { "members._id": str(validate_object_id(user_oid)) },
        {
            "name": 1,
            "date": 1,
            "_id": 1,
            "status": 1,
            "type": 1,
            "members.$": 1,
        }
    ).to_list(None)

    for activity in all_activities:
        activity["_id"] = str(activity["_id"])

    return {
        "status": "ok",
        "code": 200,
        "data": all_activities,
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
            'onCampus': result['on-campus'],
            'offCampus': result['off-campus'],
            'socialPractice': result['social-practice'],
            'trophy': result['trophy'],
            'total': result['total'],
        },
    }


@router.get("/{user_oid}/notification")
async def read_notifications(user_oid: str, user=Depends(get_current_user)):
    """
    Get Notifications
    """
    # Get notification list
    notifications = await db.zvms.notifications.find().to_list(2000)

    if user_oid != user["id"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = []
    for notification in notifications:
        notification["_id"] = str(notification["_id"])
        if str(user_oid) in notification["receivers"] or notification["global"]:
            result.append(notification)

    return {
        "status": "ok",
        "code": 200,
        "data": result,
    }


@router.get("/{user_oid}/imgtoken") # deprecated
async def get_imgtoken(
    user_oid: str,
    user=Depends(get_current_user),
):
    # 根据用户的权限和 ID 获取图片上传 Token
    per = 1  # 管理员权限
    if "admin" not in user["per"] and user["id"] != validate_object_id(user_oid):
        per = 0  # 普通用户
    token = get_img_token(user_oid, per)
    return {
        "status": "ok",
        "code": 200,
        "data": token,
    }

@router.put("/image")
async def upload_image(
    request: Request,
    user=Depends(get_current_user),
):
    # 上传图片
    form = await request.form()
    image = form.get("image")
    if not isinstance(image, UploadFile):
        raise HTTPException(status_code=400, detail="No image file provided")
    filename = randomString() + '.jpg'
    path = os.path.join(config.UPLOAD_FOLDER, filename)
    with open(path, 'wb') as buffer:
        buffer.write(await image.read())
    image_process.compress(path, path, config.MAX_SIZE)
    fileId = image_storage.upload(path)
    if not fileId:
        raise HTTPException(status_code=500, detail="Image storage failed")
    timestamp = int(time.time())
    # 添加到用户信息
    db.zvms.users.update_one(
        {"_id": validate_object_id(user["id"])},
        {"$push": {"images": {"fileId": fileId, "timestamp": timestamp}}},
    )
    # 清空缓存
    if os.path.exists(path):
        os.remove(path)
    return {
        "status": "ok",
        "code": 200,
        "data": fileId,
    }

@router.get("/image/show/{fileId}")
async def show_image(
    fileId: str,
    user=Depends(get_current_user),
):
    # 判断用户是否登录
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # 获取图片
    image = image_storage.getBBImage(fileId)
    if image.status_code != 200:
        raise HTTPException(status_code=image.status_code, detail=image.text)
    else:
        def generate():
            for chunk in image.iter_content(chunk_size=1024):
                yield chunk
        return StreamingResponse(generate(), media_type="image/jpeg")

@router.get("/image/{user_oid}")
async def read_images(
    user_oid: str,
    user=Depends(get_current_user),
):
    # 获取用户的图片列表
    if user["id"] != user_oid and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})
    return {
        "status": "ok",
        "code": 200,
        "data": user["images"],
    }

@router.delete("/image/{fileId}")
async def delete_image(
    fileId: str,
    user=Depends(get_current_user),
):
    # 删除图片
    flag = False
    user = await db.zvms.users.find_one({"_id": validate_object_id(user["id"])})
    images = user["images"]
    for image in images:
        if image["fileId"] == fileId:
            images.remove(image)
            image_storage.remove(fileId)
            flag = True
            break
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user["id"])},
        {"$set": {"images": images}},
    )
    if flag:
        return {
            "status": "ok",
            "code": 200,
        }
    else:
        raise HTTPException(status_code=404, detail="Image not found")
