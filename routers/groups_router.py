import re
import tempfile
from io import BytesIO
from typing import Optional
import pandas as pd
from fastapi.responses import FileResponse
from typings.export import ExportFormat
from typings.group import Group
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from database import db
from pydantic import BaseModel

from util.calculate import calculate_time
from util.cert import check_password
from util.get_class import get_activities_related_to_user

from util.object_id import (
    compulsory_temporary_token,
    get_current_user,
    validate_object_id,
)

router = APIRouter()


@router.post("")
async def create_group(payload: Group, user=Depends(get_current_user)):
    """
    Create a user group
    """

    if not "admin" in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    group = payload.model_dump()

    result = await db.zvms.groups.insert_one(group)

    id = str(result.inserted_id)

    return {
        "status": "ok",
        "code": 201,
        "data": {"_id": id},
    }


@router.get("")
async def get_groups(
    page: int = 1,
    perpage: int = 10,
    type="all",
    search="",
    user=Depends(get_current_user),
):
    """
    Get all groups
    """

    if len(user["per"]) == 0:
        raise HTTPException(status_code=403, detail="Permission denied")

    if type == "all":
        target = ["permission", "class"]
    elif type == "permission":
        target = ["permission"]
    elif type == "class":
        target = ["class"]
    else:
        raise HTTPException(status_code=400, detail="Invalid type")

    count = await db.zvms.groups.count_documents(
        {"name": {"$regex": search, "$options": "i"}}
    )

    pipeline = [
        {
            "$match": {
                "type": {"$in": target},
                "name": {"$regex": search, "$options": "i"},
            },
        },
        {"$project": {"description": 0}},
        {"$sort": {"name": 1}},
        {"$skip": 0 if page < 1 else (page - 1) * perpage},
        {"$limit": count if page < 1 else perpage},
    ]

    result = await db.zvms.groups.aggregate(pipeline).to_list(None)

    for group in result:
        group["_id"] = str(group["_id"])

    return {
        "status": "ok",
        "code": 200,
        "data": result,
        "metadata": {"size": count},
    }


@router.get("/{group_id}")
async def get_group(group_id: str):
    """
    Get a group
    """

    result = await db.zvms.groups.find_one({"_id": ObjectId(group_id)})

    if result is None:
        raise HTTPException(status_code=404, detail="Group not found")

    result["_id"] = str(result["_id"])

    return {
        "status": "ok",
        "code": 200,
        "data": result,
    }


class PutGroupName(BaseModel):
    name: str


@router.put("/{group_id}/name")
async def update_group_name(
    group_id: str, payload: PutGroupName, user=Depends(get_current_user)
):
    """
    Update group name
    """

    if not "admin" in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    await db.zvms.groups.update_one(
        {"_id": validate_object_id(group_id)}, {"$set": {"name": payload.name}}
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.get("/{group_id}/activities")
async def get_class_activities(
    group_id: str,
    page: int = 1,
    perpage: int = 10,
    query: str = "",
    user=Depends(get_current_user),
):
    """
    Get activities related to a group
    """
    if query != "" and "admin" not in user["per"]:
        query = re.escape(query)

    same_class = False
    if "secretary" in user["per"]:
        target = await db.zvms.users.find_one({"_id": ObjectId(user["id"])})
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        classid = target["group"]
        if classid == group_id:
            same_class = True
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (
        "admin" not in user["per"]
        and not "auditor" in user["per"]
        and not "department" in user["per"]
        and (not "secretary" in user["per"] and not same_class)
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    result, count = await get_activities_related_to_user(
        user["id"], page, perpage, query, group_id
    )
    return {
        "status": "ok",
        "code": 200,
        "data": result,
        "metadata": {"size": count},
    }


@router.get("/{group_id}/user")
async def get_users_in_class(
    group_id: str,
    page: int = 1,
    perpage: int = 10,
    search: str = "",
    pwdm: bool = False,
    user=Depends(get_current_user),
):
    """
    Get users in a class
    """
    same_class = False
    if "secretary" in user["per"]:
        target = await db.zvms.users.find_one({"_id": ObjectId(user["id"])})
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        classid = target["group"]
        if classid == group_id:
            same_class = True
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (
        "admin" not in user["per"]
        and not "auditor" in user["per"]
        and not "department" in user["per"]
        and (not "secretary" in user["per"] and not same_class)
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    count = await db.zvms.users.count_documents(
        {"group": group_id, "name": {"$regex": search, "$options": "i"}}
    )
    pipeline = [
        {"$match": {"group": group_id, "name": {"$regex": search, "$options": "i"}}},
        {"$sort": {"id": 1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]
    result = await db.zvms.users.aggregate(pipeline).to_list(None)
    for user in result:
        user["_id"] = str(user["_id"])
        if pwdm:
            user["password"] = not check_password(user["id"], user["password"])
        else:
            user["password"] = None
    return {"status": "ok", "code": 200, "data": result, "metadata": {"size": count}}


@router.get("/{group_id}/time")
async def get_user_times_in_class(
    group_id: str,
    page: int = 1,
    perpage: int = 10,
    exceeding: bool = True,
    shortage: bool = False,
    start: Optional[str] = None,
    end: Optional[str] = None,
    search: str = "",
    user=Depends(get_current_user),
):
    """
    Get users in a class
    """
    same_class = False
    if "secretary" in user["per"]:
        target = await db.zvms.users.find_one({"_id": ObjectId(user["id"])})
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        classid = target["group"]
        if classid == group_id:
            same_class = True
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (
        "admin" not in user["per"]
        and not "auditor" in user["per"]
        and not "department" in user["per"]
        and (not "secretary" in user["per"] and not same_class)
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    count = await db.zvms.users.count_documents(
        {"group": group_id, "name": {"$regex": search, "$options": "i"}}
    )
    pipeline = [
        {"$match": {"group": group_id, "name": {"$regex": search, "$options": "i"}}},
        {"$sort": {"id": 1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]
    result = await db.zvms.users.aggregate(pipeline).to_list(None)
    time = []
    for user in result:
        if start is not None and end is not None:
            user_time = await calculate_time(str(user["_id"]), (start, end))
        else:
            user_time = await calculate_time(str(user["_id"]))
        if exceeding or shortage:
            more_on_campus = min(
                round(max(user_time["off-campus"] - 15, 1) / 2, 0), 6.0
            )
            more_off_campus = min(
                round(max(user_time["on-campus"] - 25, 1) / 3, 0), 6.0
            )
            user_time["on-campus"] += more_on_campus
            user_time["off-campus"] += more_off_campus
        if shortage:
            user_time["on-campus"] = max(25 - user_time["on-campus"], 0)
            user_time["off-campus"] = max(15 - user_time["off-campus"], 0)
            user_time["social-practice"] = max(18 - user_time["social-practice"], 0)
        group = await db.zvms.groups.find_one(
            {
                "_id": {"$in": list(map(lambda x: ObjectId(x), user["group"]))},
                "type": "class",
            }
        )
        if group is None:
            continue
        doc = {
            "_id": str(user["_id"]),
            "name": user["name"],
            "id": str(user["id"]),
            "group": group["name"],
            "on-campus": user_time["on-campus"],
            "off-campus": user_time["off-campus"],
            "social-practice": user_time["social-practice"],
        }
        time.append(doc)
    return {"status": "ok", "code": 200, "data": time, "metadata": {"size": count}}


class PutGroupDescription(BaseModel):
    description: str


@router.put("/{group_id}/description")
async def update_group_description(
    group_id: str, payload: PutGroupDescription, user=Depends(get_current_user)
):
    """
    Update group description
    """

    if not "admin" in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    await db.zvms.groups.update_one(
        {"_id": ObjectId(group_id)}, {"$set": {"description": payload.description}}
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.delete("/{group_id}")
async def delete_group(group_id: str, user=Depends(compulsory_temporary_token)):
    """
    Remove group
    """

    if not "admin" in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    await db.zvms.groups.delete_one({"_id": ObjectId(group_id)})

    return {
        "status": "ok",
        "code": 200,
    }


@router.get("/{group_id}/template")
async def get_group_template(
    group_id: str, export_format: ExportFormat, user=Depends(get_current_user)
):
    same_class = False
    if "secretary" in user["per"]:
        target = await db.zvms.users.find_one({"_id": ObjectId(user["id"])})
        if target is None:
            raise HTTPException(status_code=404, detail="User not found")
        classid = target["group"]
        if classid == group_id:
            same_class = True
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if (
        "admin" not in user["per"]
        and not "auditor" in user["per"]
        and not "department" in user["per"]
        and (not "secretary" in user["per"] and not same_class)
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    db_users = await db.zvms.users.find({"group": group_id}).to_list(None)

    group_name = (await db.zvms.groups.find_one({"_id": ObjectId(group_id)}))["name"]

    users = []

    for user in db_users:
        users.append(
            {
                "_id": str(user["_id"]),
                "ID": user["id"],
                "Name": user["name"],
                "Class": group_name,
                "On Campus": None,
                "Off Campus": None,
                "Social Practice": None,
            }
        )

    table = pd.DataFrame(users).sort_values("ID")

    buffer = BytesIO()
    with tempfile.NamedTemporaryFile(
        suffix=f".{export_format.suffix()}", delete=False
    ) as tmp:
        if export_format == ExportFormat.excel:
            table.to_excel(tmp.name, index=False)
        elif export_format == ExportFormat.csv:
            table.to_csv(tmp.name, index=False)
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
        tmp.seek(0)
        buffer.write(tmp.read())

    return FileResponse(tmp.name, media_type=export_format.mime())
