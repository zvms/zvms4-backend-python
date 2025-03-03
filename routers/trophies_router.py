from typings.activity import ActivityMode
from typings.trophy import (
    Trophy,
    TrophyAward,
    TrophyMember,
    TrophyMemberStatus,
    TrophyStatus,
)
from bson import ObjectId
from database import db
from fastapi import HTTPException, APIRouter, Depends
from util.group import is_in_a_same_class
from util.object_id import compulsory_temporary_token, get_current_user, validate_object_id
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


@router.post("")
async def create_trophy(request: Trophy, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")

@router.get("")
async def get_trophies(user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")

@router.get("/{trophy_oid}")
async def get_trophy(trophy_oid: str, user=Depends(get_current_user)):
    raise HTTPException(status_code=410, detail="Gone")

class PutStatus(BaseModel):
    status: TrophyStatus


@router.put("/{trophy_oid}/status")
async def update_trophy_status(
    trophy_oid: str, request: PutStatus, user=Depends(get_current_user)
):
    raise HTTPException(status_code=410, detail="Gone")

class PutName(BaseModel):
    name: str


@router.put("/{trophy_oid}/name")
async def update_trophy_name(
    trophy_oid: str, request: PutName, user=Depends(get_current_user)
):
    raise HTTPException(status_code=410, detail="Gone")

@router.delete("/{trophy_oid}")
async def delete_trophy(trophy_oid: str, user=Depends(compulsory_temporary_token)):
    raise HTTPException(status_code=410, detail="Gone")

@router.post("/{trophy_oid}/member")
async def add_trophy_member(
    trophy_oid: str, member: TrophyMember, user=Depends(get_current_user)
):
    raise HTTPException(status_code=410, detail="Gone")

class PutMemberStatus(BaseModel):
    status: TrophyMemberStatus


@router.put("/{trophy_oid}/member/{member_oid}/status")
async def update_trophy_member_status(
    trophy_oid: str,
    member_oid: str,
    request: PutMemberStatus,
    user=Depends(get_current_user),
):
    raise HTTPException(status_code=410, detail="Gone")

class PutTrophyMemberMode(BaseModel):
    mode: ActivityMode


@router.put("/{trophy_oid}/member/{member_oid}/mode")
async def update_trophy_member_mode(
    trophy_oid: str,
    member_oid: str,
    request: PutTrophyMemberMode,
    user=Depends(get_current_user),
):
    raise HTTPException(status_code=410, detail="Gone")

@router.delete("/{trophy_oid}/member/{member_oid}")
async def delete_trophy_member(
    trophy_oid: str, member_oid: str, user=Depends(compulsory_temporary_token)
):
    raise HTTPException(status_code=410, detail="Gone")

@router.post("/{trophy_oid}/award")
async def add_trophy_award(
    trophy_oid: str, award: TrophyAward, user=Depends(get_current_user)
):
    raise HTTPException(status_code=410, detail="Gone")

@router.delete("/{trophy_oid}/award/{award_oid}")
async def delete_trophy_award(
    trophy_oid: str, award_oid: str, user=Depends(compulsory_temporary_token)
):
    raise HTTPException(status_code=410, detail="Gone")

class PutTrophyAwardDuration(BaseModel):
    duration: float


@router.put("/{trophy_oid}/award/{award_oid}/duration")
async def update_trophy_award_duration(
    trophy_oid: str,
    award_oid: str,
    request: PutTrophyAwardDuration,
    user=Depends(get_current_user),
):
    raise HTTPException(status_code=410, detail="Gone")
