from typings.activity import (
    Activity,
    ActivityStatus,
    ActivityType,
    MemberActivityStatus,
    SpecialActivityClassify,
)
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Form, Request
from typing import List
from util.get_class import get_activities_related_to_user
from utils import get_current_user, validate_object_id, timestamp_change
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from database import db
from pydantic import BaseModel, Field
from typing import Optional
import settings

router = APIRouter()


@router.post("")
async def create_activity(payload: Activity, user=Depends(get_current_user)):
    """
    创建义工
    """

    # remove _id

    none_permission = len(user["per"]) == 1 and "student" in user["per"]
    only_secretary = (
        len(user["per"]) == 2
        and "secretary" in user["per"]
        and "student" in user["per"]
    )

    payload.creator = user["id"]

    if payload.type == ActivityType.special and payload.special is None:
        raise HTTPException(
            status_code=400, detail="Special activity must have a classify"
        )

    if payload.type == ActivityType.specified and payload.registration is None:
        raise HTTPException(
            status_code=400, detail="Specified activity must have a registration"
        )

    if (
        none_permission
        and payload.type == ActivityType.social
        or payload.type == ActivityType.scale
    ):
        payload.status = ActivityStatus.pending
    elif (
        none_permission
        and payload.type == ActivityType.specified
        or payload.type == ActivityType.special
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    elif (
        only_secretary
        and payload.type == ActivityType.social
        or payload.type == ActivityType.scale
    ):
        payload.status = ActivityStatus.effective
    elif only_secretary and payload.type == ActivityType.specified:
        payload.status = ActivityStatus.pending
    elif only_secretary and payload.type == ActivityType.special:
        raise HTTPException(status_code=403, detail="Permission denied")
    elif (
        "admin" not in user["per"]
        and payload.type == ActivityType.special
        and payload.special is not None
        and payload.special.classify is not None
        and payload.special.classify == SpecialActivityClassify.import_
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    diction = payload.dict()

    members = diction["members"]

    for member in members:
        member["_id"] = member["id"]
        del member["id"]

    diction["members"] = members

    # Crezate activity
    result = await db.zvms.activities.insert_one(diction)

    id = result.inserted_id

    return {"status": "ok", "code": 201, "data": str(id)}


@router.put("/{activity_oid}/description")
async def change_activity_description(
    activity_oid: str, description: str = Form(...), user=Depends(get_current_user)
):
    """
    修改义工描述
    """
    # 用户权限检查
    if user["id"] != validate_object_id(activity_oid) and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改义工描述
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {
            "$set": {
                "description": description,
                "updatedAt": int(datetime.now().timestamp()),
            }
        },
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.put("/{activity_oid}/name")
async def change_activity_title(
    activity_oid: str, name: str = Form(...), user=Depends(get_current_user)
):
    """
    修改义工标题
    """
    # 用户权限检查
    if user["id"] != validate_object_id(activity_oid) and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改义工标题
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {"$set": {"name": name, "updatedAt": int(datetime.now().timestamp())}},
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.put("/{activity_oid}/status")
async def change_activity_status(
    activity_oid: str, status: str = Form(...), user=Depends(get_current_user)
):
    """
    修改义工状态
    """

    target_activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )
    # 用户权限检查
    if (
        "secretary" not in user["per"]
        and "department" not in user["per"]
        and "admin" not in user["per"]
        and (target_activity["type"] == "social" or target_activity["type"] == "scale")
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if (
        "department" not in user["per"]
        and "admin" not in user["per"]
        and (target_activity["type"] == "specified")
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改义工状态
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {"$set": {"status": status, "updatedAt": int(datetime.now().timestamp())}},
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.get("")
async def read_activities(
    type: str | None,
    mode: str,
    user=Depends(get_current_user),
):
    """
    返回义工列表
    """

    print(type, range, mode, user)

    # User permission check
    if (
        "admin" not in user["per"]
        and "auditor" not in user["per"]
        and "department" not in user["per"]
        and mode == "campus"
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    elif (
        "secretary" not in user["per"]
        and "admin" not in user["per"]
        and mode == "class"
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    if mode == "campus":
        # 读取义工列表
        cursor = db.zvms.activities.find()
        activities = await cursor.to_list(length=1500)
        result = list()
        for activity in activities:
            activity["_id"] = str(activity["_id"])
            if type is None or activity["type"] == type or type == "all":
                # 遍历 activity 将所有 $OID 转换为 str
                for key in activity:
                    if isinstance(activity[key], ObjectId):
                        activity[key] = str(activity[key])
                result.append(activity)
        return {"status": "ok", "code": 200, "data": result}
    elif mode == "class":
        result = await get_activities_related_to_user(user["id"])
        return {"status": "ok", "code": 200, "data": result}


@router.get("/{activity_oid}")
async def read_activity(activity_oid: str, user=Depends(get_current_user)):
    """
    返回义工信息
    """
    # 读取义工信息
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # 遍历 activity 将所有 $OID 转换为 str
    for key in activity:
        if isinstance(activity[key], ObjectId):
            activity[key] = str(activity[key])
    return {"status": "ok", "code": 200, "data": activity}


@router.post("/{activity_oid}/member")
async def user_activity_signup(activity_oid: str, user=Depends(get_current_user)):
    """
    用户报名义工
    """

    # 读取义工信息
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    # 用户是否可报名 [registration/classes/遍历]
    _flag = False
    for i in activity["registration"]["classes"]:
        if str(user["class"]) == str(i["class"]):
            _flag = True
            break
    if not _flag:
        raise HTTPException(status_code=403, detail="Permission denied, not in class.")

    # 名额是否已满 [registration/classes/class=xxx/limit]
    _flag = False
    for i in activity["registration"]["classes"]:
        if str(user["class"]) == str(i["class"]):
            if len(activity["members"]) < i["max"]:
                _flag = True
                break
    if not _flag:
        raise HTTPException(status_code=403, detail="Permission denied, full.")

    # 义工报名
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {
            "$addToSet": {
                "members": {
                    "_id": str(user["id"]),
                    "status": "draft",
                    "impression": "",
                    "mode": "on-campus",  # TODO: Need to be fixed
                    "history": list(),
                    "images": list(),
                }
            }
        },
    )

    # POST 请求无需返回值


@router.delete("/{activity_oid}/member/{uid}")
async def user_activity_signoff(
    activity_oid: str, uid: str, user=Depends(get_current_user)
):
    """
    用户取消义工
    """

    # 检测用户是否报名
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )
    if not any(member["_id"] == str(user["id"]) for member in activity["members"]):
        raise HTTPException(
            status_code=403, detail="Permission denied, not in activity."
        )

    # 权限检查
    if user["id"] != str(validate_object_id(uid)) and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 义工删除 mongodb 操作
    members = activity["members"]
    members = [member for member in members if member["_id"] != str(user["id"])]

    # 更新数据库中的文档
    result = await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)}, {"$set": {"members": members}}
    )

    return {
        "status": "ok",
        "code": 200,
    }


class PutImpression(BaseModel):
    impression: str


@router.put("/{activity_oid}/member/{id}/impression")
async def user_impression_edit(
    activity_oid: str,
    id: str,
    impression: PutImpression,
    user=Depends(get_current_user),
):
    """
    用户修改义工反思
    """

    result = impression.impression

    # 获取义工信息
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    # 检查用户是否在义工中
    _flag = False
    for member in activity["members"]:
        if member["_id"] == id:
            _flag = True
            break
    if not _flag:
        raise HTTPException(
            status_code=403, detail="Permission denied, not in activity."
        )

    # 检查用户权限
    if user["id"] != str(validate_object_id(id)) and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改义工反思
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid), "members._id": id},
        {"$set": {"members.$.impression": result}},
    )

    return {
        "status": "ok",
        "code": 200,
    }


class PutStatus(BaseModel):
    status: MemberActivityStatus


@router.put("/{activity_oid}/member/{user_oid}/status")
async def user_status_edit(
    activity_oid: str, user_oid: str, payload: PutStatus, user=Depends(get_current_user)
):
    """
    用户修改义工状态
    """

    # 获取新状态
    status = payload.status

    # 获取义工信息
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    print(activity["members"])

    # 检查用户是否在义工中
    _flag = False
    for member in activity["members"]:
        print(member["_id"], user_oid)
        if member["_id"] == user_oid:
            _flag = True
            break
    if not _flag:
        raise HTTPException(status_code=400, detail="User not in activity")

    # 检查用户权限
    if (
        "auditor" not in user["per"]
        and "admin" not in user["per"]
        and status != "pending"
        and status != "draft"
    ):
        raise HTTPException(
            status_code=403, detail="Permission denied, not enough permission"
        )

    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    member = None

    for i in activity["members"]:
        if i["_id"] == user_oid:
            member = i
            break

    if member is None:
        raise HTTPException(status_code=400, detail="User not in activity")

    if member["status"] == "effective" or member["status"] == "refused":
        raise HTTPException(status_code=400, detail="User status cannot be changed")

    if user["id"] != user_oid and (status == "draft" or status == "pending"):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. This action is only allowed to be done by the user himself / herself",
        )

    # 修改义工状态
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid), "members._id": user_oid},
        {"$set": {"members.$.status": status}},
    )

    return {
        "status": "ok",
        "code": 200,
    }

    # PUT 请求无需返回值


@router.delete("/{activity_oid}")
async def delete_activity(activity_oid: str, user=Depends(get_current_user)):
    """
    Remove activity
    """

    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if (
        user["id"] != activity["creator"]
        and "admin" not in user["per"]
        and "department" not in user["per"]
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await db.zvms.activities.delete_one(
        {"_id": validate_object_id(activity_oid)}
    )

    return {
        "status": "ok",
        "code": 200,
    }
