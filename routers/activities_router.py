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


@router.post("/")
async def create_activity(request: Request, user=Depends(get_current_user)):
    """
    创建义工
    """
    payload = await request.json()
    activity_info = {
        "type": payload["type"],
        "name": payload["name"],
        "description": payload["description"],
        "date": await timestamp_change(payload["date"]),
        "members": list(),
        "createdAt": int(datetime.now().timestamp()),
        "updatedAt": int(datetime.now().timestamp()),
        "creator": validate_object_id(user["_id"]),
        "status": payload["status"],
        "registration": payload["registration"],
        "special": payload["special"],
    }

    # 用户权限检查
    if activity_info["special"] == "other" and user["permission"] < 2:
        raise HTTPException(status_code=403, detail="Permission denied")

    if activity_info["special"] == "prize" and user["permission"] < 4:
        raise HTTPException(status_code=403, detail="Permission denied")

    if activity_info["special"] == "club" and user["permission"] < 4:
        raise HTTPException(status_code=403, detail="Permission denied")

    if activity_info["special"] == "deduction" and user["permission"] < 8:
        raise HTTPException(status_code=403, detail="Permission denied")

    if activity_info["special"] == "import" and user["permission"] < 16:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 返回创建的 ObjectID
    result = await db.zvms.activities.insert_one(activity_info)
    return {"id": str(result.inserted_id)}


@router.put("/{activity_oid}/description")
async def change_activity_description(
    activity_oid: str, description: str = Form(...), user=Depends(get_current_user)
):
    """
    修改义工描述
    """
    # 用户权限检查
    if user["permission"] < 2:
        raise HTTPException(status_code=403, detail="Permission denied")
    if user["_id"] != validate_object_id(activity_oid) and user["permission"] < 16:
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

    # PUT 请求无需返回值


@router.put("/{activity_oid}/name")
async def change_activity_title(
    activity_oid: str, name: str = Form(...), user=Depends(get_current_user)
):
    """
    修改义工标题
    """
    # 用户权限检查
    if user["permission"] < 2:
        raise HTTPException(status_code=403, detail="Permission denied")
    if user["_id"] != validate_object_id(activity_oid) and user["permission"] < 16:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改义工标题
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {"$set": {"name": name, "updatedAt": int(datetime.now().timestamp())}},
    )

    # PUT 请求无需返回值


@router.put("/{activity_oid}/status")
async def change_activity_status(
    activity_oid: str, status: str = Form(...), user=Depends(get_current_user)
):
    """
    修改义工状态
    """
    # 用户权限检查
    if user["permission"] < 2:
        raise HTTPException(status_code=403, detail="Permission denied")
    if user["_id"] != validate_object_id(activity_oid) and user["permission"] < 16:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改义工状态
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {"$set": {"status": status, "updatedAt": int(datetime.now().timestamp())}},
    )

    # PUT 请求无需返回值


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
        result = await get_activities_related_to_user(user["_id"])
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
                    "_id": str(user["_id"]),
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
    if not any(member["_id"] == str(user["_id"]) for member in activity["members"]):
        raise HTTPException(
            status_code=403, detail="Permission denied, not in activity."
        )

    # 权限检查
    if user["_id"] != validate_object_id(uid) and user["permission"] < 16:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 义工删除 mongodb 操作
    members = activity["members"]
    members = [member for member in members if member["_id"] != str(user["_id"])]

    # 更新数据库中的文档
    result = await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)}, {"$set": {"members": members}}
    )

    # DELETE 请求无需返回值


@router.put("/{activity_oid}/member/{id}/impression")
async def user_impression_edit(
    activity_oid: str,
    id: str,
    impression: str = Form(...),
    user=Depends(get_current_user),
):
    """
    用户修改义工反思
    """

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
    if user["_id"] != validate_object_id(id) and user["permission"] < 16:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改义工反思
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid), "members._id": id},
        {"$set": {"members.$.impression": impression}},
    )

    # PUT 请求无需返回值


@router.put("/{activity_oid}/member/{user_oid}/status")
async def user_status_edit(
    activity_oid: str, user_oid: str, request: Request, user=Depends(get_current_user)
):
    """
    用户修改义工状态
    """

    # 获取新状态
    payload = await request.json()
    status = payload["status"]

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

    if user["id"] != user_oid and status == "draft" or status == "pending":
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
