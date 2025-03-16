import re
from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from bcrypt import hashpw, gensalt
from routers.activities_router import user_activity_signoff
from typings.log import inject_log, ZVMSLog
from typings.user import User
from util.calculate import calculate_time
from util.group import is_in_a_same_class
from util.logify import binding_user_credentials
from util.object_id import (
    compulsory_temporary_token,
    get_current_user,
    validate_object_id,
    string_to_option_object_id, optional_current_user
)
from database import db
from util.cert import get_hashed_password_by_cert, validate_by_cert
from util.user import get_user_name
from util.validation import validate_past_identity, validate_number, validate_student_name

router = APIRouter()


class AuthUser(BaseModel):
    id: str
    mode: str
    credential: str


@router.post("/auth")
async def auth_user(auth: AuthUser, request: Request, meta=Depends(binding_user_credentials)):
    id = auth.id
    mode = auth.mode
    credential = auth.credential

    log = ZVMSLog(str(request.url), auth.id, meta['clarity_id'], f'''User {await get_user_name(id)} is logging in''',
                  meta['ip'], datetime.timestamp(datetime.now()))

    if mode is None:
        mode = "long"

    if string_to_option_object_id(id) is None:
        users = await db.zvms.users.find({"id": id}).to_list(None)
        if len(users) != 1:
            raise HTTPException(status_code=404,
                                detail="The id of the user is not found, or there are multiple users with the same id.")
        id = str(users[0]["_id"])

    result = await validate_by_cert(id, credential, mode)

    await log.insert_log()

    return {
        "token": result,
        "_id": id,
    }


@router.post("")
async def create_user(
    target_user: User,
    actioner=Depends(compulsory_temporary_token),
    log=Depends(inject_log)
):
    # Check user's permission
    if "admin" not in actioner["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    document = target_user.model_dump()

    id = str(document['id'])
    document['id'] = id
    document['password'] = hashpw(id.encode('utf-8'), gensalt()).decode('utf-8')


    if not validate_number(document['id'])[0]:
        raise HTTPException(status_code=400, detail=validate_number(document['id'])[1])
    if not validate_student_name(document['name'])[0]:
        raise HTTPException(status_code=400, detail=validate_student_name(document['name'])[1])

    log.with_text(f'''User {target_user.name} is created by {await get_user_name(actioner['id'])}''')
    await log.insert_log()

    result = await db.zvms.users.insert_one(document)

    return {
        "status": "ok",
        "code": 201,
        "data": str(result.inserted_id)
    }


@router.delete("/{target}")
async def delete_user(
    target: str,
    user=Depends(compulsory_temporary_token),
    log=Depends(inject_log)
):
    if target == user['id']:
        raise HTTPException(status_code=400, detail='You can\'t delete yourself.')
    validate_object_id(target)
    # Remove all activity records of the user
    metadata = await read_user_activity(target, page=-1, user=user, query='', perpage=1000)
    for activity in metadata['data']:
        await user_activity_signoff(str(activity['_id']), uid=target, user=user, log=log)
    await db.zvms.users.delete_one({"_id": validate_object_id(target)})
    log.with_text(f'''User {await get_user_name(target)} ({target}) is deleted by {await get_user_name(user['id'])}''')
    await log.insert_log()
    return {
        "status": "ok",
        "code": 200
    }


class PutPassword(BaseModel):
    credential: str


@router.put("/{user_oid}/password")
async def change_password(
    user_oid: str, credential: PutPassword, user=Depends(compulsory_temporary_token), log=Depends(inject_log)
):
    log.with_text(f'''User {await get_user_name(user_oid)}'s password is changed''')
    await log.insert_log()
    # Validate user's permission
    secretary = "secretary" in user["per"] and (
        is_in_a_same_class(user["id"], user_oid)
    )
    modification = user["id"] == user_oid and user["scope"] == "temporary_token"
    if (
        "admin" not in user["per"]
        and (not modification)
        and "department" not in user["per"]
        and "auditor" not in user["per"]
        and (not secretary)
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    password = await get_hashed_password_by_cert(credential.credential)

    # Get origin user's permissions: if admin, should reject the request
    forbid_groups = await db.zvms.groups.find({"permission": {"$in": ['admin', 'system']}}).to_list(None)
    target = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if target["group"] in forbid_groups and user["id"] != str(target['_id']):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Change user's password
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user_oid)}, {"$set": {"password": str(password)}}
    )

    return {
        "status": "ok",
        "code": 200,
    }


@router.get("")
async def read_users(query: str = '', page: int = 1, perpage: int = 5, privilege: bool = False,
                     user: Optional[str] = Depends(optional_current_user)):
    """
    Query users
    """
    if privilege:
        groups = await db.zvms["groups"].find({
            'permissions': {
                '$in': ['admin', 'department']
            }
        })
        selected = []
        for group in groups:
            selected.append(str(group['_id']))
    count = await db.zvms.users.count_documents({
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"id": {"$regex": query, "$options": "i"}},
            {"past": {"$elemMatch": {"$regex": query, "$options": "i"}}}
        ] if user is not None else [
            # should not search if not login.
            {"id": query}
        ],
    })
    result = (
        await db.zvms["users"]
        .find(
            {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"id": {"$regex": query, "$options": "i"}},
                    {"past": {"$elemMatch": {"$regex": query, "$options": "i"}}}
                ] if user is not None else [
                    # should not search if not login.
                    {"id": query}
                ],
            },
            {
                "name": True,
                "id": True,
                "group": True,
            },
        )
        .sort({"id": 1})
        .skip(0 if page == -1 else (page - 1) * perpage)
        .limit(perpage if page == -1 else perpage)
        .to_list(0 if page == -1 else perpage)
    )

    for user in result:
        user["_id"] = str(user["_id"])

    return {"status": "ok", "code": 200, "data": result, "metadata": {"size": count}}


@router.get("/{user_oid}")
async def read_user(user_oid: str):
    """
    Return user's information
    """
    # Read user's information
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user["_id"] = str(user["_id"])
    del user["password"]
    return {
        "status": "ok",
        "code": 200,
        "data": user,
    }


class PutUser(BaseModel):
    name: str
    id: str
    group: list[str]


@router.put("/{user_oid}")
async def update_user(user_oid: str, user_struct: PutUser, user=Depends(compulsory_temporary_token),
                      log=Depends(inject_log)):
    """
    Update user's information
    """
    # Check user's permission
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    user_info = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})

    if not validate_number(user_struct.id)[0]:
        raise HTTPException(status_code=400, detail=validate_number(user_struct.id)[1])
    if not validate_student_name(user_struct.name)[0]:
        raise HTTPException(status_code=400, detail=validate_student_name(user_struct.name)[1])

    pasts = []

    if user_info['name'] != user_struct.name:
        pasts.append(user_info['name'])
    if user_info['id'] != user_struct.id:
        pasts.append(user_info['id'])

    # Update user's information
    await db.zvms.users.update_one(
        {"_id": validate_object_id(user_oid)},
        {
            "$set": {
                "name": user_struct.name,
                "id": user_struct.id,
                "group": user_struct.group,
            },
            "$push": {
                "past": {
                    "$each": pasts
                }
            }
        },
    )

    log.with_text(f'''User {await get_user_name(user_oid)}'s data is updated to {user_struct.model_dump()}''')
    await log.insert_log()

    return {
        "status": "ok",
        "code": 200,
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


@router.get("/{user_oid}/activities")
async def read_user_activity(
    user_oid: str,
    user=Depends(get_current_user),
    page: int = -1,
    perpage: int = 10,
    query: str = "",
):
    """
    Return user's activities
    """
    # Check user's permission

    if "admin" not in user["per"] and "department" not in user["per"] and user["id"] != str(
        validate_object_id(user_oid)):
        raise HTTPException(status_code=403, detail="Permission denied")

    if query != '' and 'admin' not in user['per']:
        query = re.escape(query)

    count = await db.zvms.activities.count_documents(
        {"members._id": str(validate_object_id(user_oid))},
        # {"name": {"$regex": query}},
    )
    # Read user's activities
    pipeline = [
        {
            '$match': {
                'members._id': user_oid,
                'name': {'$regex': query, '$options': 'i'},
            }
        },
        {
            '$project': {
                'name': 1,
                'date': 1,
                '_id': 1,
                'status': 1,
                'type': 1,
                'special': 1,
                'members': {
                    '$filter': {
                        'input': '$members',
                        'as': 'member',
                        'cond': {'$eq': ['$$member._id', user_oid]}
                    }
                }
            }
        },
        {
            "$sort": {
                "_id": -1
            }
        },
        {'$skip': 0 if page == -1 else (page - 1) * perpage},
    ]
    if page != -1:
        pipeline.append({'$limit': perpage})

    all_activities = (
        await db.zvms.activities.aggregate(pipeline).to_list(None if page == -1 else perpage)
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
async def read_user_time(
    user_oid: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    user=Depends(get_current_user)
):
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

    if (start is not None and end is None) or (start is None and end is not None):
        raise HTTPException(status_code=400, detail="Invalid query")

    if start is not None and end is not None:
        result = await calculate_time(user_oid, (start, end))
    else:
        result = await calculate_time(user_oid)
    return {
        "status": "ok",
        "code": 200,
        "data": {
            "onCampus": result["on-campus"],
            "offCampus": result["off-campus"],
            "socialPractice": result["social-practice"],
            "total": result["total"],
        },
    }

@router.get("/{user_oid}/logs")
async def read_logs(
    user_oid: str,
    page: int = -1,
    perpage: int = 10,
    query: str = "",
    user=Depends(get_current_user),
):
    
