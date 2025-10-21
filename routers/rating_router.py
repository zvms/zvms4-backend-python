from fastapi import APIRouter, HTTPException, Depends, Query
from typings.rating import ActivityRating
from util.object_id import (
    get_current_user,
)

router = APIRouter()


@router.post("")
async def create_rating(rating: ActivityRating, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")


@router.get("")
async def get_ratings(
    page: int = Query(1, ge=1, description="Page number for pagination"),
    perpage: int = Query(10, ge=1, le=100, description="Number of items per page"),
    user=Depends(get_current_user),
):
    raise HTTPException(status_code=410, detail="Gone")
