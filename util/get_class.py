from fastapi import HTTPException
from database import db
from utils import validate_object_id

async def get_activities_related_to_user(user_oid: str):
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})
    if not user:
        return HTTPException(status_code=404, detail="User not found")

    user_group = user["group"]
    class_id = None

    for group in user_group:
        group = await db.zvms.groups.find_one({"_id": validate_object_id(group)})
        if group["type"] == "class":
            class_id = group["_id"]
            break

    if not class_id:
        return HTTPException(status_code=404, detail="User not in any class")

    users = await db.zvms.users.find({"group": str(class_id)}).to_list(None)

    activities = await db.zvms.activities.find({
        'members._id': {
            '$in': [str(user["_id"]) for user in users]
        }
    }).to_list(None)

    for activity in activities:
        activity["_id"] = str(activity["_id"])

    return activities

