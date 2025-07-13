from collections import defaultdict
from datetime import datetime
from typing import Any

from config import BASE_ON_CAMPUS, BASE_OFF_CAMPUS, BASE_SOCIAL_PRACTICE
from database import db
from settings import LANGUAGE
from utils import validate_object_id


async def calculate_user_time(
    user_id: str,
    date_start: datetime | None = None,
    date_end: datetime | None = None,
    allow_cache: bool = True,
    attach_description: bool = False,
):
    """
    Get user time

    :param user_id: User ID
    :param date_start: Start date for filtering activities
    :param date_end: End date for filtering activities
    :param allow_cache: If True, do not use cached data
    :param attach_description: If True, attach description to the result

    :return: User time
    """
    print(f"Calculating time for user {user_id} with date range {date_start} to {date_end}, allow_cache={allow_cache}, attach_description={attach_description}")
    if allow_cache and date_start is None and date_end is None:
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
    description = ''
    if attach_description:
        desc = []
        for collection in collections:
            activity = await db.zvms_new.get_collection("activities").find_one(
                {"_id": validate_object_id(collection["activity"])}
            )
            if LANGUAGE == 'zh-CN':
                modes = {
                    'on-campus': '校内',
                    'off-campus': '校外',
                    'social-practice': '社会实践',
                }
                desc.append(f"{activity['name']}（{activity['date'].strftime('%Y-%m-%d')}），{modes.get(collection['mode'], "未知")} {collection['duration']} 小时")
            else:
                desc.append(
                    f"{activity['name']} (at {activity['date'].strftime('%Y-%m-%d')}), {collection['mode']} {collection['duration']} hours")
        if LANGUAGE == 'zh-CN':
            description = "；".join(desc)
        elif len(desc) == 0:
            description = "No activities found"
        elif len(desc) == 1:
            description = desc[0]
        elif len(desc) == 2:
            description = " and ".join(desc)
        else:
            description = ", ".join(desc[:-1]) + " and " + desc[-1]
    result = defaultdict(float)
    result["on-campus"] = 0
    result["off-campus"] = 0
    result["social-practice"] = 0
    for m in collections:
        result[m["mode"]] += m["duration"]
    result = dict(result)
    if attach_description:
        result["description"] = description

    await db.zvms_new.get_collection("time").delete_many({"user": user_id})

    await db.zvms_new.get_collection("time").insert_one(
        {
            "user": user_id,
            "on_campus_raw": result["on-campus"],
            "off_campus_raw": result["off-campus"],
            "social_practice": result["social-practice"],
            "updated_at": datetime.now(),
        },
    )

    return result


def find_percentile_threshold(percentiles: dict[str, float], target: float, mode: str) -> float:
    thresholds = {
        'on-campus': BASE_ON_CAMPUS,
        'off-campus': BASE_OFF_CAMPUS,
        'social-practice': BASE_SOCIAL_PRACTICE,
    }
    if target >= thresholds[mode]:
        return 100
    percentiles = sorted(percentiles.items(), key=lambda item: item[1], reverse=True)
    for key, value in percentiles:
        if target >= value:
            return int(key.replace("%", ""))
    return 100
