import re
from fastapi import APIRouter, Depends
from database import db
from util.calculate import calculate_user_time
from util.object_id import get_current_user
from collections import defaultdict
from util.permission.user import validate_read_user_permission

router = APIRouter()


@router.get("/{user_id}/activities")
async def get_user_activities_v2(
    user_id: str,
    page: int = 1,
    perpage: int = 10,
    search: str = "",
    sort: str = "_id",
    regex: bool = True,
    asc: bool = False,
    user=Depends(get_current_user),
):
    """
    Get user activities
    :param user_id: User ID
    :param page: The page number
    :param perpage: Items per page
    :param search: Search keyword
    :param sort: Sort by field
    :param regex: Use regex for search
    :param asc: Sort in ascending order
    :param user: Current user
    """
    await validate_read_user_permission(user, user_id, "volunteer")

    # Check if the user has permission to view the activities
    # skipped right now

    if not regex:
        search = re.escape(search) if search else ""

    # Get the user activities
    activities_filter = (
        {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
            ]
        }
        if search
        else {}
    )

    selected_activities = (
        await db.zvms_new.get_collection("activities")
        .find(activities_filter)
        .to_list(None)
    )

    members_record_filter = {
        "member": user_id,
        "activity": {"$in": [str(activity["_id"]) for activity in selected_activities]},
    }

    count = await db.zvms_new.get_collection("activity_members").count_documents(
        members_record_filter
    )

    pipeline = [
        {"$match": members_record_filter},
        {
            "$addFields": {
                "activity_id_obj": {"$toObjectId": "$activity"},
            }
        },
        {
            "$lookup": {
                "from": "activities",
                "localField": "activity_id_obj",
                "foreignField": "_id",
                "as": "activity",
            }
        },
        {"$unwind": "$activity"},
        {"$project": {"activity_id_obj": 0}},
        {"$sort": {sort: 1 if asc else -1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]

    members = (
        await db.zvms_new.get_collection("activity_members")
        .aggregate(pipeline)
        .to_list(None)
    )
    activities = []

    for member in members:
        # make the `activity` as the top level field, and let `member` to be `mine` field
        activity = member.pop("activity")
        member["_id"] = str(member["_id"])
        activity["mine"] = member
        activity["_id"] = str(activity["_id"])
        activities.append(activity)

    return {
        "page": page,
        "perpage": perpage,
        "total": count,
        "activities": activities,
    }


@router.get("/{user_id}/time")
async def get_user_time_v2(user_id: str, user=Depends(get_current_user)):
    """
    Get user time

    :param user_id: User ID
    :param user: Current user

    :return: User time
    """
    await validate_read_user_permission(user, user_id, "volunteer")

    result = await calculate_user_time(user['id'])

    return result
