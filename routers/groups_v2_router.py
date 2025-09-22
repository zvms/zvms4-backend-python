import re
from collections import defaultdict
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from config import (
    BASE_OFF_CAMPUS,
    ON_TO_OFF_RATE,
    BASE_ON_CAMPUS,
    OFF_TO_ON_RATE,
    MAX_EXCEED_DISCOUNT,
    BASE_SOCIAL_PRACTICE,
)
from database import db
from typings.time import UserActivityTime
from util.calculate import calculate_user_time
from util.get_class import get_user_class
from util.object_id import get_current_user, validate_object_id
from util.permission.user import validate_read_group_permission

router = APIRouter()


@router.get("/{group_id}/activities")
async def get_group_activities_v2(
    group_id: str,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    perpage: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query("", description="Search keyword"),
    sort: str = Query("_id", description="Sort by field"),
    regex: bool = Query(True, description="Use regex for search"),
    asc: bool = Query(False, description="Sort in ascending order"),
    user=Depends(get_current_user),
):
    """
    Get group activities
    :param group_id: Group ID
    :param page: The page number
    :param perpage: Items per page
    :param search: Search keyword
    :param sort: Sort by field
    :param regex: Use regex for search
    :param asc: Sort in ascending order
    :param user: Current user
    """

    await validate_read_group_permission(user, group_id, "volunteer")

    # Get members from the group
    members = (
        await db.zvms.get_collection("users")
        .find(
            {
                "group": group_id  # TODO should be `groups` in the new structure
            }
        )
        .to_list(None)
    )

    members = [str(member["_id"]) for member in members]

    activity_members = (
        await db.zvms_new.get_collection("activity_members")
        .find({"member": {"$in": members}})
        .to_list(None)
    )

    activity_members = [
        ObjectId(activity_member["activity"]) for activity_member in activity_members
    ]

    if not regex:
        search = re.escape(search) if search else ""

    activities_filter = (
        {
            "$and": [
                {
                    "$or": [
                        {"name": {"$regex": search, "$options": "i"}},
                        {"description": {"$regex": search, "$options": "i"}},
                    ]
                },
                {"_id": {"$in": activity_members}},
            ]
        }
        if search
        else {"_id": {"$in": activity_members}}
    )

    count = await db.zvms_new.get_collection("activities").count_documents(
        activities_filter
    )

    pipeline = [
        {"$match": activities_filter},
        {"$sort": {sort: 1 if asc else -1}},
        {"$skip": (page - 1) * perpage},
        {"$limit": perpage},
    ]

    activities = (
        await db.zvms_new.get_collection("activities").aggregate(pipeline).to_list(None)
    )

    # Convert ObjectId to string
    for activity in activities:
        activity["_id"] = str(activity["_id"])

    return {
        "total": count,
        "page": page,
        "perpage": perpage,
        "activities": activities,
    }


@router.get("/{group_id}/time")
async def read_users(
    group_id: str,
    query: str = Query("", description="Search query for user name or ID"),
    page: int = Query(1, ge=-1, description="Page number for pagination"),
    perpage: int = Query(5, ge=1, le=100, description="Number of items per page"),
    allow_cache: bool = Query(True, description="Allow cached data"),
    sort: str = Query("id", description="Sort by field"),
    asc: bool = Query(True, description="Sort in ascending order"),
    user: Optional[str] = Depends(get_current_user),
):
    """
    Query users
    """
    sortkey = {
        "on-campus": "on_campus_raw",
        "off-campus": "off_campus_raw",
        "social-practice": "social_practice",
    }
    count = await db.zvms.users.count_documents(
        {
            "$or": [
                {"name": {"$regex": query, "$options": "i"}},
                {"id": {"$regex": query, "$options": "i"}},
                {"past": {"$elemMatch": {"$regex": query, "$options": "i"}}},
            ],
            "group": group_id,
        }
    )
    result = (
        await db.zvms["users"]
        .find(
            {
                "$or": [
                    {"name": {"$regex": query, "$options": "i"}},
                    {"id": {"$regex": query, "$options": "i"}},
                    {"past": {"$elemMatch": {"$regex": query, "$options": "i"}}},
                ],
                "group": group_id,
            },
            {
                "name": True,
                "id": True,
                "group": True,
            },
        )
        .to_list(None)
    )
    if sort == "id":
        result = sorted(result, key=lambda x: x["id"], reverse=not asc)
    selected_students = [str(user["_id"]) for user in result]

    user_times = (
        await db.zvms_new.get_collection("time")
        .find({"user": {"$in": selected_students}})
        .sort({sortkey.get(sort, sort): -1 if not asc else 1} if sort else None)
        .skip((page - 1) * perpage)
        .limit(perpage)
        .to_list(None)
    )
    results = []

    for user in user_times:
        user_info = await db.zvms.get_collection("users").find_one(
            {"_id": validate_object_id(user["user"])}
        )
        time_struct = UserActivityTime.model_validate(user, strict=False)
        results.append(
            {
                "_id": str(user["user"]),
                "name": user_info["name"],
                "id": user_info["id"],
                "on-campus": time_struct.on_campus,
                "off-campus": time_struct.off_campus,
                "social-practice": time_struct.social_practice,
            }
        )

    return {"status": "ok", "code": 200, "data": results, "metadata": {"size": count}}


@router.get("/{group_id}/users")
async def get_group_users_v2(
    group_id: str,
    page: int = Query(1, ge=1, description="Page number for pagination"),
    perpage: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: str = Query("", description="Search keyword"),
    sort: str = Query("id", description="Sort by field"),
    regex: bool = Query(True, description="Use regex for search"),
    asc: bool = Query(True, description="Sort in ascending order"),
    exceeding: bool = Query(True, description="Include exceeding time"),
    shortage: bool = Query(False, description="Include shortage time"),
    pwdm: bool = Query(False, description="Include password mode information"),
    start: Optional[str] = Query(None, description="Start date filter"),
    end: Optional[str] = Query(None, description="End date filter"),
    user=Depends(get_current_user),
):
    """
    Get group time
    :param group_id: Group ID
    :param page: The page number
    :param perpage: Items per page
    :param search: Search keyword
    :param sort: Sort by field
    :param regex: Use regex for search
    :param asc: Sort in ascending order
    :param user: Current user
    :param exceeding: Exceeding time
    :param shortage: Shortage time
    :param pwdm: Include password mode information
    :param start: Start date
    :param end: End date
    """

    # Get members from the group
    members = (
        await db.zvms.get_collection("users")
        .aggregate(
            [
                {
                    "$match": {
                        "$or": [
                            {"name": {"$regex": search, "$options": "i"}},
                            {"id": {"$regex": search, "$options": "i"}},
                            {"past": {"$elemMatch": {"$regex": search, "$options": "i"}}},
                        ],
                        "group": group_id  # TODO should be `groups` in the new structure
                    }
                },
                {"$sort": {sort: 1 if asc else -1}},
                {"$skip": (page - 1) * perpage},
                {"$limit": perpage},
            ]
        )
        .to_list(None)
    )

    count = await db.zvms.get_collection("users").count_documents(
        {
            "$or": [
                {"name": {"$regex": search, "$options": "i"}},
                {"id": {"$regex": search, "$options": "i"}},
                {"past": {"$elemMatch": {"$regex": search, "$options": "i"}}},
            ],
            "group": group_id  # TODO should be `groups` in the new structure
        }
    )

    for member in members:
        member["_id"] = str(member["_id"])
        if pwdm:
            member["password"] = not check_password(member["id"], member["password"])
        else:
            member["password"] = None

    return {
        "total": count,
        "page": page,
        "perpage": perpage,
        "members": members,
    }


@router.get("/{group_id}/statistics/compliance")
async def stat_group_compliance(
    group_id: str,
    # user=Depends(get_current_user),
):
    """
    Get group compliance statistics
    :param group_id: Group ID
    :param user: Current user
    """

    # await validate_read_group_permission(user, group_id, "volunteer")

    # Get members from the group
    members = (
        await db.zvms.get_collection("users")
        .find({"group": group_id})  # TODO should be `groups` in the new structure
        .to_list(None)
    )

    members = [str(member["_id"]) for member in members]

    member_time_counts = []

    on_campus = defaultdict(int)
    off_campus = defaultdict(int)
    social_practice = defaultdict(int)

    # Percentage of compliance, 0%–20%, 20%–40%, 40%–60%, 60%–80%, 80%–100%, completed.

    for member in members:
        user_time = await calculate_user_time(member, allow_cache=True)
        on_campus_range = min(
            int(user_time["on-campus"] / BASE_ON_CAMPUS * 100 // 20), 5
        )
        off_campus_range = min(
            int(user_time["off-campus"] / BASE_OFF_CAMPUS * 100 // 20), 5
        )
        social_practice_range = min(
            int(user_time["social-practice"] / BASE_SOCIAL_PRACTICE * 100 // 20), 5
        )
        on_campus[on_campus_range] += 1
        off_campus[off_campus_range] += 1
        social_practice[social_practice_range] += 1

    def convert_key_name(key: int) -> str:
        if key == 5:
            return "Completed"
        return f"{key * 20}%–{(key + 1) * 20}%"

    # Sort each category by its values (member counts)
    sorted_on_campus = dict(
        sorted(
            {convert_key_name(k): v for k, v in on_campus.items()}.items(),
            key=lambda item: item[0],
        )
    )
    sorted_off_campus = dict(
        sorted(
            {convert_key_name(k): v for k, v in off_campus.items()}.items(),
            key=lambda item: item[0],
        )
    )
    sorted_social_practice = dict(
        sorted(
            {convert_key_name(k): v for k, v in social_practice.items()}.items(),
            key=lambda item: item[0],
        )
    )

    return {
        "on-campus": sorted_on_campus,
        "off-campus": sorted_off_campus,
        "social-practice": sorted_social_practice,
    }
