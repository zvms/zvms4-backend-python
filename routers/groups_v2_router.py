import re
from collections import defaultdict
from bson import ObjectId
from fastapi import APIRouter, Depends
from database import db
from util.object_id import get_current_user

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
    sort: str = "_id",
    regex: bool = True,
    asc: bool = False,
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

    async for member in members:
        collections = (
            await db.zvms_new.get_collection("activity_members")
            .find({"member": str(member["_id"])})
            .to_list(None)
        )
        result = defaultdict(float)
        for m in collections:
            result[m["mode"]] += m["duration"]
        result = dict(result)
        members.update({"_id": str(member["_id"]), **result})

    return {
        "total": count,
        "page": page,
        "perpage": perpage,
        "members": members,
    }
