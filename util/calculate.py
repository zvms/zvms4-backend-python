from typing import Optional
from unittest import result
from datetime import datetime
from bson import ObjectId
from database import db
from util.get_class import get_user_classname


async def calculate_awards(
    user: str,
    trophies: list[dict] = [],
    activities: list[dict] = [],
    full: float = 10.0,
) -> dict[str, float]:
    # Read trophy list with `members` field (array) containing user's id (._id field in members)

    inject_trophies = [
        {
            "$match": {
                "members._id": user,
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {
                            "$and": [
                                {"$eq": ["$$member._id", user]},
                                {"$eq": ["$$member.status", "effective"]},
                            ]
                        },
                    }
                },
                "awards": True,
                "award": True,
            }
        },
    ]

    trophies = await db.zvms.trophies.aggregate(inject_trophies).to_list(None)

    inject_activities = [
        {
            "$match": {
                "members._id": user,
                "type": "special",
                "special.classify": "prize",
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {"$eq": ["$$member._id", user]},
                    }
                },
            }
        },
    ]
    activities = await db.zvms.activities.aggregate(inject_activities).to_list(None)

    awards = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "total": 0.0,
    }
    for activity in activities:
        if len(activity["members"]) == 0:
            continue
        member = activity["members"][0]
        if member["_id"] == user:
            if member["mode"] == "on-campus":
                awards["on-campus"] += member["duration"]
            elif member["mode"] == "off-campus":
                awards["off-campus"] += member["duration"]
            awards["total"] += member["duration"]

    if awards["total"] >= full:
        # Average the duration of recorded time as time limit is reached
        awards["on-campus"] = round(awards["on-campus"] / awards["total"] * full, 1)
        awards["off-campus"] = full - awards["on-campus"]
        awards["total"] = full
        return awards

    # Calculate awards
    for trophy in trophies:
        if len(trophy["members"]) == 0:
            continue
        member = trophy["members"][0]
        award_name = trophy["award"]
        for award in trophy["awards"]:
            if award["name"] == award_name:
                flag_ = False
                duration = award["duration"]
                if awards["total"] + award["duration"] > full:
                    duration = full - awards["total"]
                    flag_ = True
                if member["mode"] == "on-campus":
                    awards["on-campus"] += duration
                elif member["mode"] == "off-campus":
                    awards["off-campus"] += duration
                else:
                    break
                if flag_:
                    return awards
                awards["total"] += award["duration"]
                break
    return awards


async def calculate_special_activities(
    user: str, activities: Optional[list[dict]] = []
) -> dict[str, float]:
    # Read user's activity list
    inject = [
        {
            "$match": {
                "members._id": user,
                "type": "special",
                "status": "effective",
                "members.status": "effective",
                "special.classify": {"$ne": "prize"},
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {"$eq": ["$$member._id", user]},
                    }
                }
            }
        },
    ]
    activities = await db.zvms.activities.aggregate(inject).to_list(None)

    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
    }

    if activities is None:
        return result

    for activity in activities:
        if len(activity["members"]) == 0:
            continue
        member = activity["members"][0]
        if member["mode"] == "on-campus":
            result["on-campus"] += member["duration"]
        elif member["mode"] == "off-campus":
            result["off-campus"] += member["duration"]
        else:
            result["social-practice"] += member["duration"]

    return result


async def calculate_normal_activities(
    user: str,
    range: Optional[tuple[str, str]]=None
) -> dict[str, float]:
    # Read user's activity list

    inject = [
        {
            "$match": {
                "members._id": user,
                "status": "effective",
                "members.status": "effective",
            }
        },
        {
            "$project": {
                "members": {
                    "$filter": {
                        "input": "$members",
                        "as": "member",
                        "cond": {
                            "$and": [
                                {"$eq": ["$$member._id", user]},
                                {"$eq": ["$$member.status", "effective"]},
                            ]
                        },
                    }
                }
            }
        },
    ]
    if range is not None:
        inject[0]["$match"]["date"] = {"$gte": datetime.fromisoformat(range[0]).isoformat(), "$lte": datetime.fromisoformat(range[1]).isoformat()}
    activities = await db.zvms.activities.aggregate(inject).to_list(None)

    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
    }

    if activities is None:
        return result

    for activity in activities:
        if len(activity["members"]) == 0:
            continue
        member = activity["members"][0]
        if member["mode"] == "on-campus":
            result["on-campus"] += member["duration"]
        elif member["mode"] == "off-campus":
            result["off-campus"] += member["duration"]
        else:
            result["social-practice"] += member["duration"]

    return result


async def calculate_time(
    user: str,
    range: Optional[tuple[str, str]]=None
) -> dict[str, float]:
    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
        "trophy": 0.0,
        "total": 0.0,
    }
    normal = await calculate_normal_activities(user, range=range)
    result["on-campus"] = normal["on-campus"]
    result["off-campus"] = normal["off-campus"]
    result["social-practice"] = normal["social-practice"]
    result["total"] = (
        normal["on-campus"] + normal["off-campus"] + normal["social-practice"]
    )
    result["on-campus"] = round(result["on-campus"], 0)
    result["off-campus"] = round(result["off-campus"], 0)
    result["social-practice"] = round(result["social-practice"], 0)
    return result
