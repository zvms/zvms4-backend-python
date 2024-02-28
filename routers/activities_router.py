from typings.activity import (
    Activity,
    ActivityMember,
    ActivityStatus,
    ActivityType,
    MemberActivityStatus,
    SpecialActivityClassify,
)
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Form, Request
from typing import List
from util.get_class import get_activities_related_to_user, get_classid_by_code, get_classid_by_user_id
from utils import compulsory_temporary_token, get_current_user, validate_object_id, timestamp_change
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
    Create activity
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

    diction = payload.model_dump()

    members = diction["members"]

    for member in members:
        member["_id"] = member["id"]
        del member["id"]

    diction["members"] = members

    # Crezate activity
    result = await db.zvms.activities.insert_one(diction)

    id = result.inserted_id

    return {"status": "ok", "code": 201, "data": str(id)}


class PutDescription(BaseModel):
    description: str

@router.put("/{activity_oid}/description")
async def change_activity_description(
    activity_oid: str, payload: PutDescription, user=Depends(get_current_user)
):
    """
    Edit activity description
    """
    description = payload.description
    # Check permission
    if user["id"] != validate_object_id(activity_oid) and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Edit activity description
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


class PutActivityName(BaseModel):
    name: str

@router.put("/{activity_oid}/name")
async def change_activity_title(
    activity_oid: str, payload: PutActivityName, user=Depends(get_current_user)
):
    """
    Modify Activity Title
    """
    name = payload.name
    # Check permission
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

class PutActivityStatus(BaseModel):
    status: str

@router.put("/{activity_oid}/status")
async def change_activity_status(
    activity_oid: str, payload: PutActivityStatus, user=Depends(get_current_user)
):
    """
    Modify activity status
    """

    status = payload.status

    target_activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )
    # Check user permission
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

    # Update activity status
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
    Return activities
    """

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
    Return activity
    """
    # Read activity
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Change ObjectId to str
    for key in activity:
        if isinstance(activity[key], ObjectId):
            activity[key] = str(activity[key])
    return {"status": "ok", "code": 200, "data": activity}


@router.post("/{activity_oid}/member")
async def user_activity_signup(activity_oid: str, member: ActivityMember, user=Depends(get_current_user)):
    """
    Append user to activity
    If user doesn't have permission, regard as a registration. Check the register limit, if full, raise 403.
    If user is department, directly append user to activity if the activity is created by the department.
    If user is secretary, user is allowed to append user who is in the same class.
    Admin is allowed to append user to any activity.
    """

    # Read activity
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    target_classid = get_classid_by_user_id(user["id"])

    # Check available if user doesn't have any other permission
    _flag = False
    if 'secretary' not in user["per"] and 'admin' not in user["per"] and 'department' not in user['per']:
        for i in activity["registration"]["classes"]:
            if target_classid == i["classid"]:
                members_in_class = list(filter(lambda x: get_classid_by_user_id(x["_id"]) == target_classid, activity["members"]))
                if len(members_in_class) >= i["max"]:
                    raise HTTPException(status_code=403, detail="Permission denied, full.")
                else:
                    _flag = True
        if not _flag:
            raise HTTPException(status_code=403, detail="Permission denied, not in class.")
        else:
            member.status = MemberActivityStatus.draft
        if activity['type'] != ActivityType.specified:
            raise HTTPException(status_code=403, detail="Permission denied, cannot be appended to this activity.")
    elif 'secretary' in user["per"] and 'department' not in user["per"]:
        member.status = MemberActivityStatus.draft
        user_classid = get_classid_by_user_id(user["id"])
        target_classid = get_classid_by_user_id(member.id)
        if user_classid != target_classid:
            raise HTTPException(status_code=403, detail="Permission denied, not in class.")
        if activity['type'] == ActivityType.special:
            raise HTTPException(status_code=403, detail="Permission denied, cannot be appended to this activity.")
    elif 'department' in user["per"] or 'admin' in user["per"]:
        status = MemberActivityStatus.effective if activity['type'] == ActivityType.special else MemberActivityStatus.pending
        member.status = status
    else:
        raise HTTPException(status_code=403, detail="Permission denied.")

    diction = member.model_dump()
    diction["_id"] = diction["id"]
    del diction["id"]

    # Append user to activity
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {
            "$addToSet": {
                "members": diction
            }
        },
    )

    return {
        "status": "ok",
        "code": 201,
    }


@router.delete("/{activity_oid}/member/{uid}")
async def user_activity_signoff(
    activity_oid: str, uid: str, user=Depends(compulsory_temporary_token)
):
    """
    User exit activity or admin remove user from activity
    """

    # Check if member in activity
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    _flag = False
    for member in activity["members"]:
        if member["_id"] == uid:
            _flag = True
            break
    if not _flag:
        raise HTTPException(status_code=400, detail="User not in activity")
    # Check user permission
    if user["id"] != str(validate_object_id(uid)) and ("admin" not in user["per"] and "department" not in user["per"]):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Remove user from activity
    target = []
    for member in activity["members"]:
        if member["_id"] != uid:
            target.append(member)

    # Update activity
    result = await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)}, {"$set": {"members": target}}
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
    User modify activity impression
    """

    result = impression.impression

    # Fetch activity
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    # Check if user is in activity
    _flag = False
    for member in activity["members"]:
        if member["_id"] == id:
            _flag = True
            break
    if not _flag:
        raise HTTPException(
            status_code=403, detail="Permission denied, not in activity."
        )

    # Check user permission
    if user["id"] != str(validate_object_id(id)) and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Modify user impression
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
    User modify activity status
    """

    # Get target activity
    status = payload.status

    # Get activity information
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid)}
    )

    # Check if user is in activity
    _flag = False
    for member in activity["members"]:
        if member["_id"] == user_oid:
            _flag = True
            break
    if not _flag:
        raise HTTPException(status_code=400, detail="User not in activity")

    # Check user status
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

    # Modify user status
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid), "members._id": user_oid},
        {"$set": {"members.$.status": status}},
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.delete("/{activity_oid}")
async def delete_activity(activity_oid: str, user=Depends(compulsory_temporary_token)):
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
