import re
from collections import defaultdict
from datetime import datetime
from typing import Literal, cast
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from database import db
from typings.activity_v2 import Activity, ActivityMember
from typings.log import inject_log
from typings.user import User as UserV1
from util.object_id import get_current_user, compulsory_temporary_token
from util.permission import volunteer, volunteer_member
from util.user import get_user_name
from util.validation import validate_activity_name
from utils import validate_object_id

router = APIRouter()


@router.post("")
async def create_activity_v2(
    activity: Activity, user=Depends(get_current_user), log=Depends(inject_log)
):
    """
    :param activity: Activity object to be created
    :param user: Current user
    :param log: Logger object

    :return: Created activity ID

    The new version of the activity creation endpoint, using the latest data model.
    """
    await volunteer.validate_create_permission(user, activity.type == "hybrid")

    activity.status = "pending"

    validated, reason = validate_activity_name(activity.name)

    if not validated:
        raise HTTPException(status_code=400, detail=reason)

    activity.creator = str(user["id"])

    activity = activity.model_dump()

    result = await db.zvms_new.get_collection("activities").insert_one(activity)

    log.with_text(
        f'User {await get_user_name(user['id'])} (ID: {user['id']}) created activity {activity["name"]} at {datetime.now().isoformat()} (ID: {result.inserted_id}).'
    )
    await log.insert_log()

    return JSONResponse({"id": str(result.inserted_id)}, status_code=201)


@router.get("")
async def get_activities_v2(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    perpage: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query("", description="Search string for filtering activities"),
    sort: str = Query("_id", description="Sort field"),
    asc: bool = Query(False, description="Sort order (ascending or descending)"),
    regex: bool = Query(False, description="Whether to use regex for searching"),
    activity_type: str = Query("all", description="Type of activity to filter by"),
    user=Depends(get_current_user),
):
    """
    :param user: Current user
    :param page: Page number for pagination
    :param perpage: Number of items per page
    :param search: Search string for filtering activities
    :param sort: Sort field
    :param asc: Sort order (ascending or descending)
    :param regex: Whether to use regex for searching
    :param activity_type: Type of activity to filter by

    :return: List of activities
    """

    if activity_type is None or activity_type == "all" or activity_type == "":
        target_types = ["on-campus", "off-campus", "social-practice", "hybrid"]
    else:
        target_types = activity_type.split(",")
    if len(target_types) == 0:
        target_types = ["on-campus", "off-campus", "social-practice", "hybrid"]

    if not regex:
        search = re.escape(search) if search else ""

    document_filter = {
        "$and": [
            {"name": {"$regex": search, "$options": "i"}},
            {"type": {"$in": target_types}},
        ]
    }

    count = await db.zvms_new.get_collection("activities").count_documents(
        document_filter
    )

    pipeline = [
        {"$match": document_filter},
        {"$sort": {sort: 1 if asc else -1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]

    activities = (
        await db.zvms_new.get_collection("activities").aggregate(pipeline).to_list(None)
    )

    for activity in activities:
        activity["_id"] = str(activity["_id"])

    return {
        "activities": activities,
        "total": count,
        "page": page,
        "perpage": perpage,
    }


@router.get("/{activity_id}")
async def get_activity_v2(activity_id: str, user=Depends(get_current_user)):
    """
    :param activity_id: ID of the activity to be retrieved
    :param user: Current user
    :return: Activity object
    """

    activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )
    members = await db.zvms_new.get_collection("activity_members").count_documents(
        {"activity": str(activity_id)}
    )

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    activity["_id"] = str(activity["_id"])

    return {"activity": activity, "members_count": members}


@router.delete("/{activity_id}")
async def delete_activity_v2(
    activity_id: str,
    user=Depends(get_current_user),
    log=Depends(inject_log),
):
    """
    :param activity_id: ID of the activity to be deleted
    :param user: Current user
    :param log: Logger object
    :return: Deletion status
    """

    target_activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )

    if not target_activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    await volunteer.validate_update_permission(
        user, Activity.model_validate(target_activity, strict=False)
    )

    await db.zvms_new.get_collection("activity_members").delete_many(
        {"activity": str(activity_id)}
    )

    result = await db.zvms_new.get_collection("activities").delete_one(
        {"_id": validate_object_id(activity_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Activity not found")

    log.with_text(
        f'User {await get_user_name(user["id"])} deleted activity {target_activity["name"]} at {datetime.now().isoformat()}. The ID of the activity is {activity_id}.'
    )
    await log.insert_log()

    return {"detail": "Activity deleted successfully"}


@router.get("/{activity_id}/members")
async def get_activity_members_v2(
    activity_id: str,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    perpage: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query("", description="Search string for filtering members"),
    sort: str = Query("_id", description="Sort field"),
    asc: bool = Query(True, description="Sort order (ascending or descending)"),
    regex: bool = Query(False, description="Whether to use regex for searching"),
    user=Depends(get_current_user),
):
    """
    :param activity_id: ID of the activity to be retrieved
    :param user: Current user
    :param page: Page number for pagination
    :param perpage: Number of items per page
    :param search: Search string for filtering members
    :param sort: Sort field
    :param asc: Sort order (ascending or descending)
    :param regex: Whether to use regex for searching

    :return: List of activity members
    """
    activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )

    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if not regex:
        search = re.escape(search) if search else ""

    searched_users = (
        await db.zvms.get_collection("users")
        .find(
            {
                "$or": [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"id": {"$regex": search, "$options": "i"}},
                ],
            }
            if search != ""
            else {}
        )
        .to_list(None)
    )

    document_filter = {
        "activity": str(activity_id),
        "member": {"$in": [str(user["_id"]) for user in searched_users]},
    }

    count = await db.zvms_new.get_collection("activity_members").count_documents(
        document_filter
    )

    pipeline = [
        {"$match": document_filter},
        {"$sort": {sort: 1 if asc else -1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]

    members = (
        await db.zvms_new.get_collection("activity_members")
        .aggregate(pipeline)
        .to_list(None)
    )

    for member in members:
        member["_id"] = str(member["_id"])

    return {
        "members": members,
        "total": count,
        "page": page,
        "perpage": perpage,
    }


@router.get("/{activity_id}/members/{session_id}")
async def get_activity_member_v2(
    activity_id: str,
    session_id: str,
    user=Depends(get_current_user),
):
    """
    :param activity_id: ID of the activity to be retrieved
    :param user: Current user
    :param session_id: ID of the session to be retrieved
    :return: ActivityMember object
    """

    target_member = await db.zvms_new.get_collection("activity_members").find_one(
        {
            "_id": validate_object_id(session_id),
            "activity": str(activity_id),
        }
    )

    if not target_member:
        raise HTTPException(status_code=404, detail="Activity member not found")

    target_member["_id"] = str(target_member["_id"])

    return target_member


@router.post("/{activity_id}/members")
async def add_activity_member_v2(
    activity_id: str,
    member: ActivityMember,
    user=Depends(get_current_user),
    log=Depends(inject_log),
):
    """
    :param activity_id: ID of the activity to be retrieved
    :param user: Current user
    :param member: ActivityMember object to be added
    :param log: Logger object
    :return: Activity object
    """

    target_activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )
    target_user = await db.zvms.get_collection("users").find_one(
        {"_id": validate_object_id(member.member)}
    )
    target_activity = Activity.model_validate(target_activity, strict=False)
    target_user = UserV1.model_validate(target_user, strict=False)
    await volunteer_member.validate_create_permission(
        user, target_user, target_activity
    )

    if target_activity.type != "hybrid" and target_activity.type != member.mode:
        raise HTTPException(
            status_code=400, detail="Activity type and member mode do not match"
        )

    if await db.zvms_new.get_collection("activity_members").find_one(
        {
            "member": str(member.member),
            "activity": str(activity_id),
            "mode": member.mode,
        }
    ):
        raise HTTPException(
            status_code=400, detail="User already in activity with same counting mode"
        )

    member = member.model_dump()

    result = await db.zvms_new.get_collection("activity_members").insert_one(member)
    
    log.with_text(
        f'User {await get_user_name(user["id"])} added member {target_user.name} to activity {target_activity.name} at {datetime.now().isoformat()}.'
    )
    await log.insert_log()

    return {
        "id": str(result.inserted_id),
        "count": await db.zvms_new.get_collection("activity_members").count_documents(
            {"activity": str(activity_id)}
        ),
    }


@router.delete("/{activity_id}/members/{session_id}")
async def delete_activity_member_v2(
    activity_id: str, session_id: str, user=Depends(get_current_user)
):
    """
    :param activity_id: ID of the activity to be retrieved
    :param user: Current user
    :param session_id: ID of the session. Since it's allowed to have *multiple* records in the same activity for the same
    person if the recoding mode is different, we must use another `session_id` to specify a document.
    :return: Activity object
    """
    await volunteer_member.validate_update_permission(user)

    result = await db.zvms_new.get_collection("activity_members").delete_one(
        {"_id": validate_object_id(session_id), "activity": activity_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Activity member not found")

    return {"detail": "Activity member deleted successfully"}


class PutActivityStatus(BaseModel):
    status: Literal["effective", "pending", "refused"]


@router.put("/{activity_id}/status")
async def modify_activity_status_v2(
    activity_id: str,
    status: PutActivityStatus,
    user=Depends(get_current_user),
    log=Depends(inject_log),
):
    """
    :param activity_id: ID of the activity to be retrieved
    :param user: Current user
    :param status: Status to be set
    :param log: Logger object

    :return: None
    """

    target_activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )

    if not target_activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    target_activity = Activity.model_validate(target_activity, strict=False)

    if target_activity.status != "pending" and "admin" not in user.get("perm"):
        raise HTTPException(
            status_code=400,
            detail="Activity status can only be modified from pending to effective or refused",
        )

    await volunteer.validate_check_permission(user, target_activity, strict=True)

    result = await db.zvms_new.get_collection("activities").update_one(
        {"_id": validate_object_id(activity_id)},
        {
            "$set": {
                "status": status.status,
                "approver": str(user["id"]),
                "updatedAt": datetime.now(),
            }
        },
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Activity not found")

    log.with_text(
        f'User {await get_user_name(user["id"])} updated activity {target_activity.name} at {datetime.now().isoformat()}. The ID of the activity is {activity_id}.'
    )
    await log.insert_log()

    return JSONResponse({"detail": "Activity status updated successfully"})


class AmalgamationForm(BaseModel):
    """
    Form for amalgamating multiple activities into one.

    This form is used to specify the activities to be amalgamated, the name and description of the new activity,

    :param activities: List of activity IDs to be amalgamated
    :param name: Name of the new activity
    :param description: Description of the new activity. (optional) If not provided, it will be set to the concatenation of the names of the amalgamated activities.
    :param duplicated: How to handle duplicated members. Options are 'max' (keep the maximum count) or 'merge' (sum the counts).
    :param proceedPending: Whether to proceed with pending activities. If False, only effective activities will be amalgamated; if true, the final activity will be set to pending.
    """

    activities: list[str]
    name: str
    description: str = ""
    origin: Literal[
        "labor",
        "organization",
        "tasks",
        "occasions",
        "import",
        "activities",
        "practice",
        "club",
        "prize",
        "other",
    ]
    duplicated: Literal["max", "sum"] = "max"
    proceedPending: bool = False


@router.post("/amalgamation")
async def amalgamate_activities_v2(
    form: AmalgamationForm,
    user=Depends(compulsory_temporary_token),
    log=Depends(inject_log),
):
    raise HTTPException(status_code=410, detail="Permanently removed")

class UpdateUserRecord(BaseModel):
    duration: float
    mode: Literal["on-campus", "off-campus", "social-practice"]


@router.put("/{activity_id}/members/{document_id}/record")
async def update_user_duration_v2(
    activity_id: str,
    document_id: str,
    updated: UpdateUserRecord,
    user=Depends(get_current_user),
):
    """
    Update the duration of a user's record in an activity.

    :param activity_id: ID of the activity
    :param document_id: ID of the activity member document
    :param updated: UpdateUserRecord containing the new duration and mode
    :param user: Current user
    :return: Updated activity member document
    """
    target_activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )

    if not target_activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    target_member = await db.zvms_new.get_collection("activity_members").find_one(
        {
            "_id": validate_object_id(document_id),
            "activity": str(activity_id),
        }
    )

    if not target_member:
        raise HTTPException(status_code=404, detail="Activity member not found")

    await volunteer_member.validate_update_permission(user)

    updated_data = updated.model_dump()
    updated_data["duration"] = float(updated_data["duration"])

    result = await db.zvms_new.get_collection("activity_members").update_one(
        {"_id": validate_object_id(document_id)},
        {"$set": updated_data},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Activity member not found")

    return JSONResponse({"detail": "Activity member updated successfully"})


class UpdateActivityInfo(BaseModel):
    name: str
    description: str


@router.put("/{activity_id}/info")
async def update_activity_info(
    payload: UpdateActivityInfo, activity_id: str, user=Depends(get_current_user)
):
    """
    Update the name of an activity.

    :param payload: UpdateActivityInfo containing the new name and description
    :param activity_id: ID of the activity to be updated
    :param user: Current user
    :return: Updated activity document
    """
    target_activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )

    if not target_activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    await volunteer.validate_update_permission(
        user, Activity.model_validate(target_activity, strict=False)
    )

    validated, reason = validate_activity_name(payload.name)
    if not validated:
        raise HTTPException(status_code=400, detail=reason)

    result = await db.zvms_new.get_collection("activities").update_one(
        {"_id": validate_object_id(activity_id)},
        {"$set": {"name": payload.name, "description": payload.description}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Activity not found")

    return JSONResponse({"detail": "Activity name updated successfully"})
