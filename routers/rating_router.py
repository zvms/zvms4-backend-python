from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from typings.notification import Notification
from typings.rating import ActivityRating
from util.object_id import (
    compulsory_temporary_token,
    get_current_user,
    validate_object_id,
)
from database import db
from pydantic import BaseModel

router = APIRouter()


@router.post("")
async def create_rating(rating: ActivityRating, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")


@router.get("")
async def get_ratings(page: int = 1, perpage: int = 10, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")
