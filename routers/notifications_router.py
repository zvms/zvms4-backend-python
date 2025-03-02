from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request
from typings.notification import Notification
from util.object_id import compulsory_temporary_token, get_current_user, validate_object_id
from database import db
from pydantic import BaseModel

router = APIRouter()


@router.post("")
async def create_notification(request: Notification, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")


@router.get("")
async def get_notifications(
    page: int = 1, perpage: int = 10, user=Depends(get_current_user)
):
    raise HTTPException(status_code=410, detail="Gone")

@router.get("/{notification_oid}")
async def get_notification(notification_oid: str, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")

class PutContent(BaseModel):
    content: str


class PutTitle(BaseModel):
    title: str


@router.put("/{notification_oid}/content")
async def update_notification_content(
    notification_oid: str, request: PutContent, user=Depends(get_current_user)
):
    raise HTTPException(status_code=410, detail="Gone")

@router.put("/{notification_oid}/title")
async def update_notification_title(
    notification_oid: str, request: PutTitle, user=Depends(get_current_user)
):
    raise HTTPException(status_code=410, detail="Gone")

@router.delete("/{notification_oid}")
async def delete_notification(
    notification_oid: str, user=Depends(compulsory_temporary_token)
):
    raise HTTPException(status_code=410, detail="Gone")
    
