from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from typings.notification import Notification
from typings.rating import ActivityRating
from utils import compulsory_temporary_token, get_current_user, validate_object_id
from database import db
from pydantic import BaseModel

router = APIRouter()

@router.post("")
async def create_rating(rating: ActivityRating, user=Depends(get_current_user)):
    if 'admin' not in user['per'] and 'department' not in user['per'] and 'rating' not in user['elg']:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Find duplicated document, if exists, return bad request
    redunants = await db.zvms.ratings.find({
        "activity_id": rating.activity_id,
        "user_id": rating.user_id
    }).to_list(None)

    if len(redunants) > 0:
        raise HTTPException(status_code=400, detail="Duplicated rating")

    if rating.user_id != user['id']:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Create rating
    rating = rating.model_dump()
    await db.zvms.ratings.insert_one(rating)
    return {
        "status": "ok",
        "code": 201,
        "data": {"_id": str(rating["_id"])},
    }


@router.get("")
async def get_ratings(
    page: int = 1, perpage: int = 10, user=Depends(get_current_user)
):
    if "admin" not in user["per"] or "rating" not in user["elg"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Get ratings
    count = await db.zvms.ratings.count_documents({})
    result = (
        await db.zvms.ratings.find()
        .sort("_id", -1)
        .skip(0 if page == -1 else (page - 1) * perpage)
        .limit(0 if page == -1 else perpage)
        .to_list(None if page == -1 else perpage)
    )
    for i in result:
        i["_id"] = str(i["_id"])
    return {
        "status": "ok",
        "code": 200,
        "data": result,
        "metadata": {
            "size": count,
        },
    }
