import re
from collections import defaultdict
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends

from config import (
    BASE_OFF_CAMPUS,
    ON_TO_OFF_RATE,
    BASE_ON_CAMPUS,
    OFF_TO_ON_RATE,
    MAX_EXCEED_DISCOUNT,
    BASE_SOCIAL_PRACTICE,
)
from database import db
from util.calculate import calculate_user_time
from util.object_id import get_current_user
from util.permission.user import validate_read_group_permission

router = APIRouter()


@router.get("/{group_id}/activities")
async def get_group_activities_v2(
    group_id: str,
    page: int = 1,
    perpage: int = 10,
    search: str = "",
    sort: str = "_id",
    regex: bool = True,
    asc: bool = False,
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
async def get_group_time_v2(
    group_id: str,
    page: int = 1,
    perpage: int = 10,
    search: str = "",
    sort: str = "id",
    regex: bool = True,
    asc: bool = True,
    exceeding: bool = True,
    shortage: bool = False,
    start: Optional[str] = None,
    end: Optional[str] = None,
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
    :param start: Start date
    :param end: End date
    """

    await validate_read_group_permission(user, group_id, "volunteer")

    # Get members from the group
    members = (
        await db.zvms.get_collection("users")
        .aggregate(
            [
                {
                    "$match": {
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
            "group": group_id  # TODO should be `groups` in the new structure
        }
    )

    date_filter = {}

    if start and end:
        date_filter["date"] = {
            "$gte": start,
            "$lte": end,
        }

    filtered_activities = (
        await db.zvms_new.get_collection("activities")
        .find({"status": "effective", **date_filter})
        .to_list(None)
    )

    filtered_activities = [str(activity["_id"]) for activity in filtered_activities]

    times = []
    for member in members:
        collections = (
            await db.zvms_new.get_collection("activity_members")
            .find(
                {
                    "member": str(member["_id"]),
                    "status": "effective",
                    "activity": {"$in": filtered_activities},
                }
            )
            .to_list(None)
        )
        result = defaultdict(float)
        result["on-campus"] = 0
        result["off-campus"] = 0
        result["social-practice"] = 0
        for m in collections:
            result[m["mode"]] += m["duration"]
        result = dict(result)
        if exceeding:
            more_on_campus = min(
                round(
                    max(result["off-campus"] - BASE_OFF_CAMPUS, 1) * OFF_TO_ON_RATE, 0
                ),
                MAX_EXCEED_DISCOUNT,
            )
            more_off_campus = min(
                round(max(result["on-campus"] - BASE_ON_CAMPUS, 1) * ON_TO_OFF_RATE, 0),
                MAX_EXCEED_DISCOUNT,
            )
            result["on-campus"] += more_on_campus
            result["off-campus"] += more_off_campus
        if shortage:
            result["on-campus"] = max(BASE_ON_CAMPUS - result["on-campus"], 0)
            result["off-campus"] = max(BASE_OFF_CAMPUS - result["off-campus"], 0)
            result["social-practice"] = max(
                BASE_SOCIAL_PRACTICE - result["social-practice"], 0
            )
        times.append(
            {
                "_id": str(member["_id"]),
                "name": member["name"],
                "id": member["id"],
                **result,
            }
        )

    return {
        "total": count,
        "page": page,
        "perpage": perpage,
        "members": times,
    }


@router.get("/{group_id}/users")
async def get_group_users_v2(
    group_id: str,
    page: int = 1,
    perpage: int = 10,
    search: str = "",
    sort: str = "id",
    regex: bool = True,
    asc: bool = True,
    exceeding: bool = True,
    shortage: bool = False,
    start: Optional[str] = None,
    end: Optional[str] = None,
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
            "group": group_id  # TODO should be `groups` in the new structure
        }
    )

    for member in members:
        member["_id"] = str(member["_id"])

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
