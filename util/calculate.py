from unittest import result
from database import db

async def calculate_awards(user: str, full: float = 10.0):
    # Read trophy list with `members` field (array) containing user's id (._id field in members)
    trophies = await db.zvms.trophies.find({"members._id": user}).to_list(None)
    activities = await db.zvms.activities.find(
        {"members._id": user, "type": "special", "special.classify": "prize"}
    ).to_list(None)
    awards = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "total": 0.0,
    }
    for activity in activities:
        for member in activity["members"]:
            if member["_id"] == user:
                if member["status"] != "effective":
                    break
                if member["mode"] == "on-campus":
                    awards["on-campus"] += member["duration"]
                elif member["mode"] == "off-campus":
                    awards["off-campus"] += member["duration"]
                else:
                    break
                awards["total"] += member["duration"]
                break
    if awards['total'] >= full:
        # Average the duration of recorded time as time limit is reached
        awards['on-campus'] = round(awards['on-campus'] / awards['total'] * full, 1)
        awards['off-campus'] = full - awards['on-campus']
        awards['total'] = full
        return awards
    # Calculate awards
    for trophy in trophies:
        trophy_member = trophy["members"]
        for member in trophy_member:
            if member["_id"] == user:
                if member["status"] != "effective":
                    break
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
                break
    return awards


async def calculate_special_activities(user: str):
    # Read user's activity list
    activities = await db.zvms.activities.find(
        {"members._id": user, "type": "special", "special.classify": {"$ne": "prize"}}
    ).to_list(None)

    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
    }

    for activity in activities:
        for member in activity["members"]:
            if member["_id"] == user:
                if member["status"] != "effective":
                    break
                if member["mode"] == "on-campus":
                    result["on-campus"] += member["duration"]
                elif member["mode"] == "off-campus":
                    result["off-campus"] += member["duration"]
                else:
                    result["social-practice"] += member["duration"]
                break

    return result


async def calculate_normal_activities(user: str):
    # Read user's activity list
    activities = await db.zvms.activities.find(
        {"members._id": user, "type": {"$ne": "special"}}
    ).to_list(None)

    result = {
        "on-campus": 0.0,
        "off-campus": 0.0,
        "social-practice": 0.0,
    }

    for activity in activities:
        for member in activity["members"]:
            if member["_id"] == user:
                if member["status"] != "effective":
                    break
                if member["mode"] == "on-campus":
                    result["on-campus"] += activity["duration"]
                elif member["mode"] == "off-campus":
                    result["off-campus"] += activity["duration"]
                else:
                    result["social-practice"] += activity["duration"]
                break

    return result
