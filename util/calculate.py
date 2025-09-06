from collections import defaultdict
from datetime import datetime
from typing import Any, Literal
from config import BASE_ON_CAMPUS, BASE_OFF_CAMPUS, BASE_SOCIAL_PRACTICE
from database import db
from settings import LANGUAGE
from typings.time import UserActivityTime
from utils import validate_object_id
import pandas as pd


async def generate_description(user_id: str):
    collections = (
        await db.zvms_new.get_collection("activity_members")
        .find(
            {
                "member": user_id,
                "status": "effective",
            }
        )
        .to_list(None)
    )
    desc = []
    for collection in collections:
        activity = await db.zvms_new.get_collection("activities").find_one(
            {"_id": validate_object_id(collection["activity"])}
        )
        if LANGUAGE == "zh-CN":
            modes = {
                "on-campus": "校内",
                "off-campus": "校外",
                "social-practice": "社会实践",
            }
            desc.append(
                f"{activity['name']}（{activity['date'].strftime('%Y-%m-%d')}），{modes.get(collection['mode'], "未知")} {collection['duration']} 小时"
            )
        else:
            desc.append(
                f"{activity['name']} (at {activity['date'].strftime('%Y-%m-%d')}), {collection['mode']} {collection['duration']} hours"
            )
    if LANGUAGE == "zh-CN":
        description = "；".join(desc)
    elif len(desc) == 0:
        description = "No activities found"
    elif len(desc) == 1:
        description = desc[0]
    elif len(desc) == 2:
        description = " and ".join(desc)
    else:
        description = ", ".join(desc[:-1]) + " and " + desc[-1]
    return description


async def calculate_user_time_with_origin(
    user_id: str,
    allow_cache: bool = False,
    load_cache: bool = True
):
    """
    Get user time with origin data

    :param user_id: User ID
    :param allow_cache: If True, do not use cached data
    :param load_cache: If True, load the calculated data into cache

    :return: User time with origin data
    """
    print(f"Calculating time for user {user_id}.")
    cache_data = await db.zvms_new.get_collection("time_with_origin").find_one({"user": user_id}) if allow_cache else None
    if cache_data:
        return cache_data['data']
    db_data = await db.zvms_new.get_collection("activity_members").find({"member": user_id}).to_list(None)
    categorize_by_origin = {} # (certain origin) -> { 'on-campus': float, 'off-campus': float, 'social-practice': float }
    for data in db_data:
        activity = await db.zvms_new.get_collection("activities").find_one(
            {"_id": validate_object_id(data["activity"])}
        )
        origin = activity.get('origin', 'unknown')
        if origin not in categorize_by_origin:
            categorize_by_origin[origin] = {
                "on-campus": 0.0,
                "off-campus": 0.0,
                "social-practice": 0.0
            }
        categorize_by_origin[origin][data['mode']] += data['duration']
    # Convert `categorize_by_origin` to DataFrame
    df = pd.DataFrame.from_dict(categorize_by_origin, orient='index').fillna(0)
    # Find percentage of each origin and mode, result format analog to the original, but the data is not raw hours, but percentage
    total = df.sum().sum()
    percentage = df.sum(axis=1) / total * 100 if total > 0 else pd.Series(0, index=df.index)
    result = {
        "by_origin": df.to_dict(orient='index'),
        "percentage_by_origin": percentage.to_dict()
    }
    if load_cache:
        db.zvms_new.get_collection("time_with_origin").delete_many({"user": str(user_id)})
        db.zvms_new.get_collection("time_with_origin").insert_one(
            {
                "user": str(user_id),
                "data": result,
                "updated_at": datetime.now(),
            },
        )
    return result


async def time_with_origin(
    scope: Literal["grade", "group"],
    scope_id: str,
    require_percentage: int = 0,
):
    """
    Get certain scope time with origin data

    :param scope: Scope type, either "grade" or "group"
    :param scope_id: Scope ID. For `grade`, it is the four-digit number of entry year; for `group`, it is the ObjectID of group.
    :param require_percentage: If > 0, only count students whose total time percentage is greater than this value
    """
    print(f"Calculating time for scope {scope} with id {scope_id}.")
    if scope == "grade":
        users = (
            await db.zvms.get_collection("users")
            .find(
                {
                    # id starts with scope_id
                    "id": {"$regex": f"^{scope_id}"},
                }
            )
            .to_list(None)
        )
    elif scope == "group":
        users = (
            await db.zvms.get_collection("users")
            .find(
                {
                    "group": scope_id,
                }
            )
            .to_list(None)
        )
    for user in users:
        await calculate_user_time_with_origin(str(user["_id"]), allow_cache=require_percentage == 0, load_cache=require_percentage == 0)
        if require_percentage > 0:
            user_time = await calculate_user_time(str(user["_id"]), allow_cache=True)
            validated = UserActivityTime(
                on_campus_raw=user_time["on-campus"],
                off_campus_raw=user_time["off-campus"],
                social_practice=user_time["social-practice"],
                updated_at=datetime.now(),
                user=str(user["_id"]),
                _id=''
            )
            if validated.percentage < require_percentage:
                users.remove(user)
                continue
    data = await db.zvms_new.get_collection("time_with_origin").find({
        "user": {"$in": [str(user["_id"]) for user in users]}
    }).to_list(None)
    df_list = []
    for item in data:
        df = pd.DataFrame.from_dict(item['data']['by_origin'], orient='index').fillna(0)
        df_list.append(df)
    print(df_list)
    if not df_list:
        return {
            "by_origin": {},
            "percentage_by_origin": {}
        }
    combined_df = pd.concat(df_list).groupby(level=0).sum()
    total = combined_df.sum().sum()
    percentage = combined_df.sum(axis=1) / total * 100 if total > 0 else pd.Series(0, index=combined_df.index)
    result = {
        "by_origin": combined_df.to_dict(orient='index'),
        "percentage_by_origin": percentage.to_dict()
    }
    db.zvms_new.get_collection("time_with_origin_stat").delete_many({"id": f"{scope}_{scope_id}_{require_percentage}"})
    db.zvms_new.get_collection("time_with_origin_stat").insert_one(
        {
            "id": f"{scope}_{scope_id}_{require_percentage}",
            "scope": scope,
            "scope_id": scope_id,
            "require_percentage": require_percentage,
            "data": result,
            "updated_at": datetime.now(),
        },
    )
    return result


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
    print(
        f"Calculating time for user {user_id} with date range {date_start} to {date_end}, allow_cache={allow_cache}, attach_description={attach_description}"
    )
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

    result = defaultdict(float)
    result["on-campus"] = 0
    result["off-campus"] = 0
    result["social-practice"] = 0
    for m in collections:
        result[m["mode"]] += m["duration"]
    result = dict(result)
    if attach_description:
        description = await generate_description(user_id)
        result["description"] = description

    if not allow_cache and date_start is None and date_end is None:
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


def find_percentile_threshold(
    percentiles: dict[str, float], target: float, mode: str
) -> float:
    thresholds = {
        "on-campus": BASE_ON_CAMPUS,
        "off-campus": BASE_OFF_CAMPUS,
        "social-practice": BASE_SOCIAL_PRACTICE,
    }
    if target >= thresholds[mode]:
        return 100
    percentiles = sorted(percentiles.items(), key=lambda item: item[1], reverse=True)
    for key, value in percentiles:
        if target >= value:
            return int(key.replace("%", ""))
    return 100
