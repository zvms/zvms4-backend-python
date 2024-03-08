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
from utils import compulsory_temporary_token, get_current_user, validate_object_id
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()


@router.post("")
async def create_trophy(request: Trophy, user=Depends(get_current_user)):
    """
    Create Trophy
    """
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    request.creator = user["id"]
    if (
        "secretary" in user["per"]
        and "department" not in user["per"]
        and "admin" not in user["per"]
    ):
        request.status = TrophyStatus.pending
    elif "department" in user["per"] or "admin" in user["per"]:
        request.status = TrophyStatus.effective
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    request.createdAt = datetime.now().isoformat()
    # Create trophy
    trophy = request.model_dump()
    result = await db.zvms.trophies.insert_one(trophy)
    return {
        "status": "ok",
        "code": 201,
        "data": {"_id": str(result.inserted_id)},
    }


@router.get("")
async def get_trophies(user=Depends(get_current_user)):
    """
    Get Trophies
    """
    # Get trophies
    result = await db.zvms.trophies.find().to_list(1000)
    for i in result:
        i["_id"] = str(i["_id"])
    return {
        "status": "ok",
        "code": 200,
        "data": result,
    }


@router.get("/{trophy_oid}")
async def get_trophy(trophy_oid: str, user=Depends(get_current_user)):
    """
    Get Trophy
    """
    # Get trophy
    result = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})
    result["_id"] = str(result["_id"])
    return {
        "status": "ok",
        "code": 200,
        "data": result,
    }


class PutStatus(BaseModel):
    status: TrophyStatus


@router.put("/{trophy_oid}/status")
async def update_trophy_status(
    trophy_oid: str, request: PutStatus, user=Depends(get_current_user)
):
    """
    Update Trophy Status
    """
    if "admin" not in user["per"] or "department" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Update trophy status
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid)},
        {"$set": {"status": request.status}},
    )
    return {"status": "ok", "code": 200}


class PutName(BaseModel):
    name: str


@router.put("/{trophy_oid}/name")
async def update_trophy_name(
    trophy_oid: str, request: PutName, user=Depends(get_current_user)
):
    """
    Update Trophy Name
    """
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Update trophy name
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid)},
        {"$set": {"name": request.name}},
    )
    return {"status": "ok", "code": 200}


@router.delete("/{trophy_oid}")
async def delete_trophy(trophy_oid: str, user=Depends(compulsory_temporary_token)):
    """
    Delete Trophy
    """
    trophy = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})
    if "admin" not in user["per"] and user["id"] != trophy["creator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Delete trophy
    await db.zvms.trophies.delete_one({"_id": validate_object_id(trophy_oid)})
    return {"status": "ok", "code": 200}


@router.post("/{trophy_oid}/member")
async def add_trophy_member(
    trophy_oid: str, member: TrophyMember, user=Depends(get_current_user)
):
    """
    Add Trophy Member
    """
    activity = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})

    target = member.id
    if "admin" in user["per"] or "department" in user["per"]:
        member.status = TrophyMemberStatus.pending
        # The approval of the trophy needs to be approved by the member of department from the instructor
    elif "secretary" in user["per"] and is_in_a_same_class(user["id"], target):
        member.status = TrophyMemberStatus.pending
    elif target == user["id"]:
        member.status = TrophyMemberStatus.pending
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    diction = member.model_dump()
    diction["_id"] = diction["id"]
    del diction["id"]
    # Add trophy member
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid)},
        {"$push": {"members": diction}},
    )
    return {"status": "ok", "code": 201}


class PutMemberStatus(BaseModel):
    status: TrophyMemberStatus


@router.put("/{trophy_oid}/member/{member_oid}/status")
async def update_trophy_member_status(
    trophy_oid: str,
    member_oid: str,
    request: PutMemberStatus,
    user=Depends(get_current_user),
):
    """
    Update Trophy Member Status
    """
    trophy = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})
    if "admin" in user["per"]:
        pass
    elif "department" in user["per"] and user["id"] == trophy["create"]:
        pass
    else:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Update trophy member status
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid), "members._id": member_oid},
        {"$set": {"members.$.status": request.status}},
    )
    return {"status": "ok", "code": 200}


class PutTrophyMemberMode(BaseModel):
    mode: ActivityMode


@router.put("/{trophy_oid}/member/{member_oid}/mode")
async def update_trophy_member_mode(
    trophy_oid: str,
    member_oid: str,
    request: PutTrophyMemberMode,
    user=Depends(get_current_user),
):
    """
    Update Trophy Member Mode
    """
    if user["id"] != member_oid and "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Update trophy member mode
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid), "members._id": member_oid},
        {"$set": {"members.$.mode": request.mode}},
    )
    return {"status": "ok", "code": 200}


@router.delete("/{trophy_oid}/member/{member_oid}")
async def delete_trophy_member(
    trophy_oid: str, member_oid: str, user=Depends(compulsory_temporary_token)
):
    """
    Delete Trophy Member
    """
    trophy = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})
    if (
        "admin" not in user["per"]
        and not ("department" in user["per"] and user["id"] == trophy["creator"])
        and member_oid != user["id"]
        and not (
            "secretary" in user["per"] and is_in_a_same_class(user["id"], member_oid)
        )
    ):
        raise HTTPException(status_code=403, detail="Permission denied")
    # Delete trophy member
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid)},
        {"$pull": {"members": {"_id": member_oid}}},
    )
    return {"status": "ok", "code": 200}


@router.post("/{trophy_oid}/award")
async def add_trophy_award(
    trophy_oid: str, award: TrophyAward, user=Depends(get_current_user)
):
    """
    Add Trophy Award
    """
    trophy = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})
    if "admin" not in user["per"] and user["id"] != trophy["creator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Add trophy award
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid)},
        {"$push": {"awards": award}},
    )
    return {"status": "ok", "code": 201}


@router.delete("/{trophy_oid}/award/{award_oid}")
async def delete_trophy_award(
    trophy_oid: str, award_oid: str, user=Depends(compulsory_temporary_token)
):
    """
    Delete Trophy Award
    """
    trophy = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})
    if "admin" not in user["per"] and user["id"] != trophy["creator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Delete trophy award
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid)},
        {
            "$pull": {"awards": {"_id": award_oid}},
        },
    )
    return {"status": "ok", "code": 200}


class PutTrophyAwardDuration(BaseModel):
    duration: float


@router.put("/{trophy_oid}/award/{award_oid}/duration")
async def update_trophy_award_duration(
    trophy_oid: str,
    award_oid: str,
    request: PutTrophyAwardDuration,
    user=Depends(get_current_user),
):
    """
    Update Trophy Award Duration
    """
    trophy = await db.zvms.trophies.find_one({"_id": validate_object_id(trophy_oid)})
    if "admin" not in user["per"] and user["id"] != trophy["creator"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    # Update trophy award duration
    await db.zvms.trophies.update_one(
        {"_id": validate_object_id(trophy_oid), "awards._id": award_oid},
        {"$set": {"awards.$.duration": request.duration}},
    )
    return {"status": "ok", "code": 200}
