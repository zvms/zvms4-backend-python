from typings.activity import (
    Activity,
    ActivityMember,
    ActivityStatus,
    ActivityType,
    MemberActivityStatus,
    SpecialActivityClassify,
)
from fastapi import APIRouter, HTTPException, Depends
from util.get_class import get_activities_related_to_user
from util.group import is_in_a_same_class
from utils import compulsory_temporary_token, get_current_user, validate_object_id
from datetime import datetime
from database import db
from pydantic import BaseModel

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

    if (
        payload.type == ActivityType.social
        or payload.type == ActivityType.scale
        or payload.type == ActivityType.specified
    ):
        payload.status = ActivityStatus.pending
    elif (
        none_permission
        and payload.type == ActivityType.special
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
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

    # Edit activity title
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

    if not target_activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check user permission
    if (
        "department" not in user["per"]
        and "admin" not in user["per"]
        and (target_activity["type"] == "social" or target_activity["type"] == "scale" or target_activity["type"] == "specified")
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
    page: int = -1,
    perpage: int = 10,
    query: str = "",
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
        # Read activities
        result = []

        audit = "auditor" in user["per"] or "admin" in user["per"]

        pipeline = [
            {
                "$match": {
                    "name": {"$regex": query, "$options": "i"},
                }
            },
            {
                "$project": {
                    "name": True,
                    "status": True,
                    "date": True,
                    "type": True,
                    "special": True,
                    "members": {
                        "$filter": {
                            "input": "$members",
                            "as": "member",
                            "cond": {
                                "$or": [
                                    {
                                        "$eq": [
                                            "$$member.status",
                                            "" if not audit else "pending",
                                        ]
                                    },
                                ]
                            },
                        }
                    },
                }
            },
            {
                "$project": {
                    "name": True,
                    "status": True,
                    "date": True,
                    "type": True,
                    "special": True,
                    "members._id": True,
                    "members.status": True,
                }
            },
            {
                "$addFields": {
                    "pendingCount": {
                        "$size": {
                            "$filter": {
                                "input": "$members",
                                "as": "member",
                                "cond": {"$eq": ["$$member.status", "pending"]},
                            }
                        }
                    }
                }
            },
            {"$sort": {"pendingCount": -1, "_id": -1}},
            {"$skip": 0 if page == -1 else (page - 1) * perpage},
            {"$limit": 0 if page == -1 else perpage},
        ]

        count = await db.zvms.activities.count_documents(
            {"name": {"$regex": query, "$options": "i"}}
        )
        activities = await db.zvms.activities.aggregate(pipeline).to_list(None)
        for activity in activities:
            activity["_id"] = str(activity["_id"])
        return {
            "status": "ok",
            "code": 200,
            "data": activities,
            "metadata": {"size": count},
        }
    elif mode == "class":
        result, count = await get_activities_related_to_user(
            user["id"], page, perpage, query
        )
        return {
            "status": "ok",
            "code": 200,
            "data": result,
            "metadata": {"size": count},
        }


@router.get("/{activity_oid}")
async def read_activity(activity_oid: str, user=Depends(get_current_user)):
    """
    Return activity
    """
    # Read activity
    pipeline = [
        {
            "$match": {
                "_id": validate_object_id(activity_oid),
            }
        },
        {
            "$addFields": {
                "members": {
                    "$map": {
                        "input": "$members",
                        "as": "member",
                        "in": {
                            "$mergeObjects": [
                                "$$member",
                                {
                                    "sortKey": {
                                        "$switch": {
                                            "branches": [
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$member.status",
                                                            "pending",
                                                        ]
                                                    },
                                                    "then": 0,
                                                },
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$member.status",
                                                            "rejected",
                                                        ]
                                                    },
                                                    "then": 1,
                                                },
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$member.status",
                                                            "refused",
                                                        ]
                                                    },
                                                    "then": 2,
                                                },
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$member.status",
                                                            "effective",
                                                        ]
                                                    },
                                                    "then": 3,
                                                },
                                                {
                                                    "case": {
                                                        "$eq": [
                                                            "$$member.status",
                                                            "draft",
                                                        ]
                                                    },
                                                    "then": 4,
                                                },
                                            ],
                                            "default": 5,  # handle unexpected statuses
                                        }
                                    }
                                },
                            ]
                        },
                    }
                }
            }
        },
        {
            "$set": {
                "members": {
                    "$sortArray": {"input": "$members", "sortBy": {"sortKey": 1}}
                }
            }
        },
        {
            "$project": {
                "members": {
                    "$map": {
                        "input": "$members",
                        "as": "member",
                        "in": {
                            "_id": "$$member._id",
                            "status": "$$member.status",
                            "duration": "$$member.duration",
                            "mode": "$$member.mode",
                        },
                    }
                },
                "name": True,
                "description": True,
                "status": True,
                "date": True,
                "type": True,
                "special": True,
                "creator": True,
                "updatedAt": True,
                "registration": True,
            }
        },
    ]
    activity = await db.zvms.activities.aggregate(pipeline).to_list(None)
    activity = activity[0]

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity["_id"] = str(activity["_id"])
    return {"status": "ok", "code": 200, "data": activity}


@router.post("/{activity_oid}/member")
async def user_activity_signup(
    activity_oid: str, member: ActivityMember, user=Depends(get_current_user)
):
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

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check available if user doesn't have any other permission
    _flag = False
    if (
        "secretary" not in user["per"]
        and "admin" not in user["per"]
        and "department" not in user["per"]
    ):
        raise HTTPException(status_code=403, detail="Permission denied.")
    elif "secretary" in user["per"] and "department" not in user["per"]:
        member.status = MemberActivityStatus.effective
        if not is_in_a_same_class(user["id"], member.id):
            raise HTTPException(
                status_code=403, detail="Permission denied, not in class."
            )
        if activity["type"] == ActivityType.special:
            raise HTTPException(
                status_code=403,
                detail="Permission denied, cannot be appended to this activity.",
            )
    elif "department" in user["per"] or "admin" in user["per"]:
        member.status = MemberActivityStatus.effective
    else:
        raise HTTPException(status_code=403, detail="Permission denied.")

    diction = member.model_dump()
    diction["_id"] = diction["id"]
    del diction["id"]

    # Append user to activity
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {"$addToSet": {"members": diction}},
    )

    return {
        "status": "ok",
        "code": 201,
    }


@router.get("/{activity_oid}/member/{uid}")
async def read_activity_user(
    activity_oid: str, uid: str, user=Depends(get_current_user)
):
    if (
        "department" not in user["per"]
        and "admin" not in user["per"]
        and "auditor" not in user["per"]
        and "inspector" not in user["per"]
        and ("secretary" not in user["per"])
        and user["id"] != str(validate_object_id(uid))
    ):
        raise HTTPException(status_code=403, detail="Permission denined.")
    activity = await db.zvms.activities.find(
        {"_id": validate_object_id(activity_oid), "members._id": uid},
        {"members.$": 1, "_id": 0},
    ).to_list(None)
    return {"status": "ok", "code": 200, "data": activity[0]["members"][0]}


@router.get("/{activity_oid}/member/{uid}/history")
async def read_user_history(
    activity_oid: str, uid: str, user=Depends(get_current_user)
):
    if (
        "department" not in user["per"]
        and "admin" not in user["per"]
        and "auditor" not in user["per"]
        and "inspector" not in user["per"]
        and ("secretary" not in user["per"])
        and user["id"] != str(validate_object_id(uid))
    ):
        raise HTTPException(status_code=403, detail="Permission denined.")
    activity = await db.zvms.activities.find_one(
        {"_id": validate_object_id(activity_oid), "members._id": uid},
        {"members.$": 1, "_id": 0},
    )
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return {"status": "ok", "code": 200, "data": activity["members"][0]["history"]}


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

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    _flag = False
    for member in activity["members"]:
        if member["_id"] == uid:
            _flag = True
            break
    if not _flag:
        raise HTTPException(status_code=400, detail="User not in activity")
    # Check user permission
    if (
        user["id"] != str(validate_object_id(uid))
        and ("admin" not in user["per"] and "department" not in user["per"])
        and ("secretary" not in user["per"] or not is_in_a_same_class(user["id"], uid))
    ):
        raise HTTPException(status_code=403, detail="Permission denied")

    # Remove user from activity
    await db.zvms.activities.update_one(
        {"_id": validate_object_id(activity_oid)},
        {"$pull": {"members": {"_id": uid}}},
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

    _ = await db.zvms.activities.delete_one(
        {"_id": validate_object_id(activity_oid)}
    )

    return {
        "status": "ok",
        "code": 200,
    }
