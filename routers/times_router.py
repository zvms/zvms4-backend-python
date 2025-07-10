from typing import Optional
from fastapi import Depends, APIRouter

from typings.time import UserActivityTime
from util.calculate import calculate_user_time
from util.object_id import (
    optional_current_user,
    validate_object_id, get_current_user,
)
from database import db

router = APIRouter()


@router.get("")
async def read_times(
    query: str = "",
    page: int = 1,
    perpage: int = 5,
    sort: str = "id",
    asc: bool = True,
    user = Depends(get_current_user),
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
            ]
            if user is not None
            else [
                # should not search if not login.
                {"id": query}
            ],
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
                ]
                if user is not None
                else [
                    # should not search if not login.
                    {"id": query}
                ],
            },
            {
                "_id": True,
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
