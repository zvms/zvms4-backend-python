from typing import Optional
from fastapi import Depends, APIRouter
from util.calculate import calculate_user_time
from util.object_id import (
    optional_current_user,
)
from database import db

router = APIRouter()


@router.get("")
async def read_users(
    query: str = "",
    page: int = 1,
    perpage: int = 5,
    allow_cache: bool = True,
    sort: str = "id",
    asc: bool = True,
    user: Optional[str] = Depends(optional_current_user),
):
    """
    Query users
    """
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
                "name": True,
                "id": True,
                "group": True,
            },
        )
        .sort(sort, 1 if asc else -1)
        .skip(0 if page == -1 else (page - 1) * perpage)
        .limit(perpage if page == -1 else perpage)
        .to_list(0 if page == -1 else perpage)
    )

    results = []

    for user in result:
        user_time = await calculate_user_time(str(user["_id"]), allow_cache=allow_cache)
        results.append(
            {
                "_id": str(user["_id"]),
                "name": user["name"],
                "id": user["id"],
                "group": user["group"],
                **user_time,
            }
        )

    return {"status": "ok", "code": 200, "data": result, "metadata": {"size": count}}
