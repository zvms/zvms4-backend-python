from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from config import MAX_QUERY_COUNT
from database import db
from util.object_id import get_current_user

router = APIRouter()


@router.get("")
async def read_logs(
    performer: str = Query("", description="Filter by performer/user"),
    page: int = Query(-1, ge=-1, description="Page number (-1 for no pagination)"),
    perpage: int = Query(10, ge=1, le=100, description="Number of items per page"),
    query: str = Query("", max_length=MAX_QUERY_COUNT, description="Search query"),
    user=Depends(get_current_user),
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    if len(query) > MAX_QUERY_COUNT:
        raise HTTPException(status_code=400, detail="Query too long")

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
