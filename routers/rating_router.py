from fastapi import APIRouter, HTTPException, Depends
from typings.rating import ActivityRating
from util.object_id import (
    get_current_user,
)

router = APIRouter()


@router.post("")
async def create_rating(rating: ActivityRating, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")


@router.get("")
async def get_ratings(page: int = 1, perpage: int = 10, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")
