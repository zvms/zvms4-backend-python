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
    if "admin" not in user["per"] and "department" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    notification = request.model_dump()
    notification["global"] = notification["global_"]
    notification["publisher"] = user["id"]
    del notification["global_"]
    del notification["id"]
    for i in notification["receivers"]:
        validate_object_id(i)
    result = await db.zvms.notifications.insert_one(notification)
    return {
        "status": "ok",
        "code": 201,
        "data": {"_id": str(result.inserted_id)},
    }


@router.get("")
async def get_notifications(
    page: int = 1, perpage: int = 10, user=Depends(get_current_user)
):
    """
    Get Notifications
    """
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Get notifications
    count = await db.zvms.notifications.count_documents({})
    result = (
        await db.zvms.notifications.find()
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


@router.get("/{notification_oid}")
async def get_notification(notification_oid: str, user=Depends(get_current_user)):
    """
    Get Notification
    """
    item = await db.zvms.notifications.find_one(
        {"_id": validate_object_id(notification_oid)}
    )
    if not item:
        raise HTTPException(status_code=404, detail="Notification not found")
    if user["id"] != item["publisher"] and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Get notification
    item["_id"] = str(item["_id"])
    return {
        "status": "ok",
        "code": 200,
        "data": item,
    }


class PutContent(BaseModel):
    content: str


class PutTitle(BaseModel):
    title: str


@router.put("/{notification_oid}/content")
async def update_notification_content(
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


@router.put("/{notification_oid}/title")
async def update_notification_title(
    notification_oid: str, request: PutTitle, user=Depends(get_current_user)
):
    """
    Update Notification Title
    """
    item = await db.zvms.notifications.find_one(
        {"_id": validate_object_id(notification_oid)}
    )
    if user["id"] != item["publisher"] and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Update notification title
    await db.zvms.notifications.update_one(
        {"_id": validate_object_id(notification_oid)},
        {"$set": {"title": request.title}},
    )


@router.delete("/{notification_oid}")
async def delete_notification(
    notification_oid: str, user=Depends(compulsory_temporary_token)
):
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
