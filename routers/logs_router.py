from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from database import db
from util.object_id import get_current_user

router = APIRouter()


@router.get("")
async def read_logs(
    performer: str = "",
    page: int = -1,
    perpage: int = 10,
    query: str = "",
    user=Depends(get_current_user),
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    query: dict[str, Any] = (
        {}
        if query == ""
        else {"$or": [{"url": {"$regex": query}}, {"data": {"$regex": query}}]}
    )
    if performer != "":
        query["user"] = performer

    count = await db.zvms.logs.count_documents(query)

    pipeline = [
        {"$match": query},
        {"$sort": {"timestamp": -1}},
        {"$skip": 0 if page == -1 else (page - 1) * perpage},
        {"$limit": perpage},
    ]

    logs = await db.zvms.logs.aggregate(pipeline).to_list(None)

    for log in logs:
        log["_id"] = str(log["_id"])

    return {
        "code": 200,
        "status": "ok",
        "data": logs,
        "metadata": {
            "size": count,
        },
    }
