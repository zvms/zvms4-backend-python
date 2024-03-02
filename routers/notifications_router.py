from fastapi import APIRouter, HTTPException, Depends, Request
from typings.notification import Notification
from utils import compulsory_temporary_token, get_current_user, validate_object_id
from database import db
from pydantic import BaseModel

router = APIRouter()


@router.post("")
async def create_notification(request: Notification, user=Depends(get_current_user)):
    """
    Create Notification
    """
    # Create notification
    if (
        request.global_
        and "admin" not in user["per"]
        and "department" not in user["per"]
        or user["id"] != request.publisher
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    notification = request.model_dump()
    notification["global"] = notification["global_"]
    notification["publisher"] = user["id"]
    for i in notification["receivers"]:
        validate_object_id(i)
    result = await db.zvms.notifications.insert_one(notification)
    return {
        "status": "ok",
        "code": 201,
        "data": {"_id": str(result.inserted_id)},
    }


@router.get("")
async def get_notifications(user=Depends(get_current_user)):
    """
    Get Notifications
    """
    # Get notifications
    result = await db.zvms.notifications.find().to_list(1000)
    for i in result:
        i["_id"] = str(i["_id"])
    return result


class PutContent(BaseModel):
    content: str


@router.put("/{notification_oid}/content")
async def update_notification(
    notification_oid: str, request: PutContent, user=Depends(get_current_user)
):
    """
    Update Notification Content
    """
    item = await db.zvms.notifications.find_one(
        {"_id": validate_object_id(notification_oid)}
    )
    if user["id"] != item["publisher"] and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Update notification content
    await db.zvms.notifications.update_one(
        {"_id": validate_object_id(notification_oid)},
        {"$set": {"content": request.content}},
    )


@router.delete("/{notification_oid}")
async def delete_notification(notification_oid: str, user=Depends(compulsory_temporary_token)):
    """
    Remove Notification
    """
    item = await db.zvms.notifications.find_one(
        {"_id": validate_object_id(notification_oid)}
    )
    if user["id"] != item["publisher"] and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Remove notification
    await db.zvms.notifications.delete_one(
        {"_id": validate_object_id(notification_oid)}
    )
