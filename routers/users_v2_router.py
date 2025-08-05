import re
from fastapi import APIRouter, Depends, HTTPException
from database import db
from util.calculate import calculate_user_time, find_percentile_threshold
from util.get_class import get_user_class
from util.object_id import get_current_user
from util.permission.user import validate_read_user_permission
from utils import validate_object_id

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
async def get_user_time_v2(
    user_id: str, user=Depends(get_current_user), allow_cache: bool = False
):
    """
    Get user time

    :param user_id: User ID
    :param user: Current user
    :param allow_cache: If True, do not use cached data

    :return: User time
    """
    await validate_read_user_permission(user, user_id, "volunteer")

    result = await calculate_user_time(user_id, allow_cache=allow_cache)

    return result


@router.get("/{user_id}/time_statistics")
async def get_user_time_statistics_v2(
    user_id: str,  # , user=Depends(get_current_user)
):
    """
    Get user time statistics, particularly `percentiles`.

    :param user_id: User ID
    :param user: Current user

    :return: User time statistics
    """
    group_id = await get_user_class(user_id)
    group_indicators = await db.zvms_new.get_collection("group_indicators").find_one(
        {"group": str(group_id)}
    )
    indicators = await db.zvms_new.get_collection("indicators").find({}).to_list(None)
    if len(indicators) == 0 or group_indicators is None:
        raise HTTPException(
            status_code=400, detail="Function temporarily unaccessible."
        )
    user_document = await db.zvms.users.find_one({"_id": validate_object_id(user_id)})
    grade_indicators = indicators[0]["percentiles"][user_document["id"][:4]]
    user_time = await calculate_user_time(user_id, allow_cache=True)
    group_indicators = group_indicators["percentiles"]
    return {
        "on-campus": {
            "value": user_time["on-campus"],
            "group": find_percentile_threshold(
                group_indicators["on-campus"], user_time["on-campus"], "on-campus"
            ),
            "grade": find_percentile_threshold(
                grade_indicators["on-campus"], user_time["on-campus"], "on-campus"
            ),
        },
        "off-campus": {
            "value": user_time["off-campus"],
            "group": find_percentile_threshold(
                group_indicators["off-campus"], user_time["off-campus"], "off-campus"
            ),
            "grade": find_percentile_threshold(
                grade_indicators["off-campus"], user_time["off-campus"], "off-campus"
            ),
        },
        "social-practice": {
            "value": user_time["social-practice"],
            "group": find_percentile_threshold(
                group_indicators["social-practice"],
                user_time["social-practice"],
                "social-practice",
            ),
            "grade": find_percentile_threshold(
                grade_indicators["social-practice"],
                user_time["social-practice"],
                "social-practice",
            ),
        },
    }
