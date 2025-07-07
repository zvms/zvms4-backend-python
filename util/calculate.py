from collections import defaultdict
from datetime import datetime
from typing import Any

from database import db


async def calculate_user_time(
    user_id: str,
    date_start: datetime | None = None,
    date_end: datetime | None = None,
    allow_cache: bool = True,
):
    """
    Get user time

    :param user_id: User ID
    :param date_start: Start date for filtering activities
    :param date_end: End date for filtering activities
    :param allow_cache: If True, do not use cached data

    :return: User time
    """
    if (not allow_cache) and date_start is None and date_end is None:
        db_data = await db.zvms_new.get_collection("time").find_one({"user": user_id})
        if db_data:
            return {
                "on-campus": db_data["on_campus_raw"],
                "off-campus": db_data["off_campus_raw"],
                "social-practice": db_data["social_practice"],
            }

    pipeline: Any = {"status": "effective"}

    if date_start and date_end:
        pipeline["date"] = {"$gte": date_start, "$lte": date_end}

    accepted_activities = (
        await db.zvms_new.get_collection("activities").find(pipeline).to_list(None)
    )
    accepted_activities = [str(activity["_id"]) for activity in accepted_activities]

    collections = (
        await db.zvms_new.get_collection("activity_members")
        .find(
            {
                "member": user_id,
                "status": "effective",
                "activity": {"$in": accepted_activities},
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

    await db.zvms_new.get_collection("time").update_one(
        {"user": user_id},
        {
            "$set": {
                "on_campus_raw": result["on-campus"],
                "off_campus_raw": result["off-campus"],
                "social_practice": result["social-practice"],
                "updated_at": datetime.now(),
            }
        },
    )

    return result
