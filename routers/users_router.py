from fastapi import APIRouter, HTTPException, Depends, Form, Request
from typing import List

from pydantic import BaseModel
from util.cases import kebab_case_to_camel_case
from util.response import generate_response
from utils import get_current_user, timestamp_change, validate_object_id
from datetime import datetime, timedelta
from jose import JWTError, jwt
from database import db
from bson import ObjectId
import settings
from util.cert import validate_by_cert

router = APIRouter()


class AuthUser(BaseModel):
    id: str
    mode: str
    credential: str


@router.post("/auth")
async def auth_user(auth: AuthUser):
    print(auth)
    print(auth.id, auth.mode, auth.credential)
    id = auth.id
    mode = auth.mode
    credential = auth.credential

    result = await validate_by_cert(id, credential)

    # 使用一个秘密密钥对负载进行签名，创建 JWT
    # token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

    # 将 JWT 作为响应返回
    print(result)
    return {
        "token": result,
        "_id": id,
    }


@router.put("/{user_oid}/password")
async def change_password(
    user_oid: str, credential: str = Form(...), user=Depends(get_current_user)
):
    """
    参数示例    值                           说明
    credential  D111C7215FC8F51F            用户新密码 (md5 测试用)
    """
    # 验证用户权限, 仅管理员可修改他人密码
    print(user)
    if "admin" not in user["per"] and user["id"] != validate_object_id(user_oid):
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改用户密码
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user_oid)}, {"$set": {"password_hashed": credential}}
    )

    # PUT 请求无需返回值


@router.put("/{user_oid}/position")
async def change_permission(
    user_oid: str, position: int = Form(...), user=Depends(get_current_user)
):
    """
    参数示例    值                           说明
    position    16                          用户新权限等级
    """
    # 验证用户权限, 仅管理员可修改他人权限
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # 修改用户权限
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user_oid)}, {"$set": {"permission": position}}
    )

    # PUT 请求无需返回值


@router.get("")
async def read_users(query: str):
    """
    返回用户列表
    """
    # 读取用户列表
    result = await db.zvms["users"].find().to_list(3000)

    print(result)
    print(query, type(query))

    query_result = []

    for user in result:
        print(
            user["name"],
            user["id"],
            query,
            query in user["name"],
            query in str(user["id"]),
        )
        if query in user["name"] or query in str(user["id"]):
            user["_id"] = str(user["_id"])
            user["password"] = ""
            query_result.append(user)

    # 返回用户列表, 排除密码
    return {"status": "ok", "code": 200, "data": query_result}


@router.get("/{user_oid}")
async def read_user(user_oid: str):
    """
    返回用户信息
    """
    # # 验证用户权限, 仅管理员可查看他人信息
    # if user["permission"] < 16 and user["_id"] != validate_object_id(user_oid):
    #     raise HTTPException(status_code=403, detail="Permission denied")

    # 读取用户信息
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})

    user["_id"] = str(user["_id"])
    user["password"] = ""
    # 返回用户信息, 排除密码
    return {
        "status": "ok",
        "code": 200,
        "data": user,
    }


@router.get("/{user_oid}/activity")
async def read_user_activity(
    user_oid: str,
    registration: bool = False,  # 是否返回报名的义工, parameters
    user=Depends(get_current_user),
):
    """
    返回用户义工列表
    """
    # 验证用户权限, 仅管理员可查看他人义工
    print(user, user["id"])
    if "admin" not in user["per"] and user["id"] != str(validate_object_id(user_oid)):
        raise HTTPException(status_code=403, detail="Permission denied")

    # 读取用户义工列表
    all_activities = await db.zvms.activities.find().to_list(1000)
    ret = list()

    # 返回用户报名的义工
    for activity in all_activities:
        _flag = False
        for member in activity["members"]:
            if member["_id"] == user_oid:
                ret.append(activity)
                _flag = True
                break
        if not registration and not _flag and "registration" in activity:
            # 义工状态可报名
            if activity["status"] == "effective" and await timestamp_change(
                activity["registration"]["deadline"]
            ) > int(datetime.utcnow().timestamp()):
                # 寻找班级
                for _ in activity["registration"]["classes"]:
                    if str(_["class"]) == str(user["class"]):
                        ret.append(activity)
                        _flag = True
                        break
        pass

    def convert_objectid_to_str(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, ObjectId):
                    data[key] = str(value)
                else:
                    convert_objectid_to_str(value)
        elif isinstance(data, list):
            for index, item in enumerate(data):
                if isinstance(item, ObjectId):
                    # 如果当前项目是一个 ObjectId，那么将它转换为字符串
                    data[index] = str(item)
                else:
                    convert_objectid_to_str(item)

    convert_objectid_to_str(ret)
    return ret


@router.get("/{user_oid}/time")
async def read_user_time(user_oid: str, user=Depends(get_current_user)):
    """
    返回用户义工时长
    """
    # 验证用户权限, 仅管理员可查看他人时长
    if "admin" not in user["per"] and user["id"] != str(validate_object_id(user_oid)):
        raise HTTPException(status_code=403, detail="Permission denied")

    # 读取用户义工时长
    user_activity = await read_user_activity(user_oid, False, user)

    # 计算用户义工时长
    ret = {"onCampus": 0, "offCampus": 0, "socialPractice": 0, "trophy": 0}

    for activity in user_activity:
        for i in activity["members"]:
            if i["_id"] == user_oid and i["status"] == "effective":
                mode = kebab_case_to_camel_case(i["mode"])
                ret[mode] += i["duration"]
                break

    return {
        "status": "ok",
        "code": 200,
        "data": ret,
    }


@router.get("/notification")
async def read_notifications(user=Depends(get_current_user)):
    """
    返回通知列表
    """
    # 读取通知列表
    result = await db.zvms.notifications.find().to_list(1000)

    # 验证是否是 recievers
    for i in range(len(result)):
        if (user["id"] not in result[i]["receivers"]) and result[i]["global"] == False:
            result.pop(i)

    return result
