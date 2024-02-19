from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Form, Request
from typing import List
from utils import get_current_user, validate_object_id, timestamp_change
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from database import db
from pydantic import BaseModel, Field
from typing import Optional
import settings

router = APIRouter()


"""
  _id: string
  global: boolean
  title: string
  content: string
  time: string // ISO-8601
  publisher: string
  receivers: string[] // ObjectId[]
  route?: string // Route to URL
  anonymous: boolean
  expire: string // ISO-8601
  type: 'pin' | 'important' | 'normal'
"""


@router.post("/")
async def create_notification(
        request: Request,
        user = Depends(get_current_user)
    ):
    """
    创建通知
    """
    # 创建通知
    payload = await request.json()
    payload.pop('_id', None)
    payload['time'] = timestamp_change(payload['time'])
    payload['expire'] = timestamp_change(payload['expire'])
    payload['publisher'] = user['_id']
    for i in range(len(payload['receivers'])):
        payload['receivers'][i] = validate_object_id(payload['receivers'][i])
    result = await db.zvms.notifications.insert_one(payload)
    return {"id": str(result.inserted_id)}


@router.get("/")
async def get_notifications(
        user = Depends(get_current_user)
    ):
    """
    获取通知列表
    """
    # 获取通知列表
    result = await db.zvms.notifications.find().to_list(1000)
    return result


@router.put("/{notification_oid}")
async def update_notification(
        notification_oid: str,
        request: Request,
        user = Depends(get_current_user)
    ):
    """
    更新通知
    """
    # 更新通知
    payload = await request.json()
    payload['time'] = timestamp_change(payload['time'])
    payload['expire'] = timestamp_change(payload['expire'])
    payload['publisher'] = user['_id']
    for i in range(len(payload['receivers'])):
        payload['receivers'][i] = validate_object_id(payload['receivers'][i])
    await db.zvms.notifications.update_one(
        {"_id": validate_object_id(notification_oid)},
        {"$set": payload}
    )


@router.delete("/{notification_oid}")
async def delete_notification(
        notification_oid: str,
        user = Depends(get_current_user)
    ):
    """
    删除通知
    """
    # 删除通知
    await db.zvms.notifications.delete_one({"_id": validate_object_id(notification_oid)})
