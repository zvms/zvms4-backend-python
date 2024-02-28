from typings.group import Group
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from database import db
from pydantic import BaseModel

from utils import compulsory_temporary_token, get_current_user

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
async def get_groups(user=Depends(get_current_user)):
    """
    Get all groups
    """

    if len(user["per"]) == 0:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await db.zvms.groups.find().to_list(1000)

    return {
        "status": "ok",
        "code": 200,
        "data": result,
    }


@router.get("/{group_id}")
async def get_group(group_id: str, user=Depends(get_current_user)):
    """
    Get a group
    """

    if len(user["per"]) == 0:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = await db.zvms.groups.find_one({"_id": ObjectId(group_id)})

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
        {"_id": ObjectId(group_id)}, {"$set": {"name": payload.name}}
    )

    return {
        "status": "ok",
        "code": 200,
    }


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
