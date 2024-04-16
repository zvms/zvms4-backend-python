from typings.group import Group
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from database import db
from pydantic import BaseModel
from util.get_class import get_activities_related_to_user

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
async def get_groups(page: int = -1, perpage: int = 10, user=Depends(get_current_user)):
    """
    Get all groups
    """

    if len(user["per"]) == 0:
        raise HTTPException(status_code=403, detail="Permission denied")

    count = await db.zvms.groups.count_documents()

    pipeline = [
        {"$sort": {"name": 1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]

    result = await db.zvms.groups.aggregate(pipeline).to_list(None)


    for group in result:
        group["_id"] = str(group["_id"])

    return {
        "status": "ok",
        "code": 200,
        "data": result,
    }


@router.get("/{group_id}")
async def get_group(group_id: str):
    """
    Get a group
    """

    result = await db.zvms.groups.find_one({"_id": ObjectId(group_id)})

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
        {"_id": ObjectId(group_id)}, {"$set": {"name": payload.name}}
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.get("/{group_id}/activity")
async def get_class_activities(
    group_id: str,
    page: int = -1,
    perpage: int = 10,
    query: str = "",
    user=Depends(get_current_user)):
    """
    Get activities related to a group
    """
    result, count = await get_activities_related_to_user(
        user["id"], page, perpage, query, group_id
    )
    return {
        "status": "ok",
        "code": 200,
        "data": result,
        "metadata": {"size": count},
    }


@router.get('/{group_id}/user')
async def get_users_in_class(group_id: str, page: int = -1, perpage: int = 10, query: str = '', user=Depends(get_current_user)):
    '''
    Get users in a class
    '''
    same_class = False
    if 'secretary' in user['per']:
        user = await db.zvms.users.find_one({'_id': ObjectId(user['_id'])})
        classid = user['group']
        if classid == group_id:
            same_class = True
    if not 'admin' in user['per'] and not 'auditor' in user['per'] and not 'department' in user['per'] and (not 'secretary' in user['per'] or not same_class):
        raise HTTPException(status_code=403, detail='Permission denied')
    count = await db.zvms.users.count_documents({'group': group_id})
    pipeline = [
        {"$match": {"group": group_id}},
        {"$sort": {"name": 1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]
    result = await db.zvms.users.aggregate(pipeline).to_list(None)
    for user in result:
        user['_id'] = str(user['_id'])
    return {
        'status': 'ok',
        'code': 200,
        'data': result,
        'metadata': {'size': count}
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
