from fastapi import HTTPException
from database import db
from utils import validate_object_id


async def get_activities_related_to_user(user_oid: str, page: int = -1, perpage: int = 10, query: str = ""):
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_group = user["group"]
    class_id = None

    grouping = await db.zvms.groups.find_one({"_id": {
        "$in": [validate_object_id(group) for group in user_group]
    }, "type": "class"})

    if grouping is None:
        raise HTTPException(status_code=404, detail="User not in any class")

    class_id = grouping["_id"]

    if not class_id:
        raise HTTPException(status_code=404, detail="User not in any class")

    users = await db.zvms.users.find({"group": str(class_id)}).to_list(None)

    count = await db.zvms.activities.count_documents({
        "members._id": {"$in": [str(user["_id"]) for user in users]},
        "name": {"$regex": query, "$options": "i"}
    })

    activities = await db.zvms.activities.find(
        {"members._id": {"$in": [str(user["_id"]) for user in users]}, "name": {"$regex": query, "$options": "i"}},
        {"name": True, "date": True, "status": True, "type": True, "special": True}
    ).sort("_id", -1).skip(0 if page == -1 else (page - 1) * perpage).limit(0 if page == -1 else perpage).to_list(None if page == -1 else perpage)

    for activity in activities:
        activity["_id"] = str(activity["_id"])

    return activities, count


async def get_user_classname(user_id: str):
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_id)})
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

    class_name = await db.zvms.groups.find_one({"_id": class_id})
    return class_name["name"]


async def get_classname(user: dict, groups: list[dict]):
    if groups is None:
        groups = await db.zvms.groups.find().to_list(None)
    if user is None:
        return None

    for group in groups:
        if str(group["_id"]) in user["group"] and group["type"] == "class":
            return group["name"]

    return None
