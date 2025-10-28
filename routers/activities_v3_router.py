from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from database import db
from typings.activity_v2 import Activity, ActivityMember
from typings.log import inject_log
from typings.user import User as UserV1
from util.object_id import get_current_user
from util.permission import volunteer_member
from util.user import get_user_name
from utils import validate_object_id

router = APIRouter()

@router.post("/{activity_id}/members")
async def add_activity_member_v3(
    activity_id: str,
    members: list[ActivityMember] = Body(),
    user=Depends(get_current_user),
    log=Depends(inject_log),
):
    """
    :param activity_id: ID of the activity to be retrieved
    :param user: Current user
    :param member: ActivityMember object to be added
    :param log: Logger object
    :return: Activity object
    """

    target_activity = await db.zvms_new.get_collection("activities").find_one(
        {"_id": validate_object_id(activity_id)}
    )

    results = []

    for member in members:    
        target_user = await db.zvms.get_collection("users").find_one(
            {"_id": validate_object_id(member.member)}
        )
        target_activity = Activity.model_validate(target_activity, strict=False)
        target_user = UserV1.model_validate(target_user, strict=False)
        await volunteer_member.validate_create_permission(
            user, target_user, target_activity
        )

        if target_activity.type != "hybrid" and target_activity.type != member.mode:
            raise HTTPException(
                status_code=400, detail="Activity type and member mode do not match"
            )
        
        existing: ActivityMember = await db.zvms_new.get_collection("activity_members").find_one(
            {
                "member": str(member.member),
                "activity": str(activity_id),
                "mode": member.mode,
            }
        )

        if existing:

            updated_data = {
                "duration": existing.duration + member.duration,
                "mode": member.mode,
            }

            result = await db.zvms_new.get_collection("activity_members").update_one(
                {"_id": validate_object_id(existing._id)},
                {"$set": updated_data},
            )

            results.append(str(existing._id))

            continue

        member_ = member.model_dump()

        result = await db.zvms_new.get_collection("activity_members").insert_one(member_)
        
        log.with_text(
            f'User {await get_user_name(user["id"])} added member {target_user.name} to activity {target_activity.name} at {datetime.now().isoformat()}.'
        )
        await log.insert_log()

        results.append(str(result.inserted_id))

    return {
        "result": results,
        "count": await db.zvms_new.get_collection("activity_members").count_documents(
            {"activity": str(activity_id)}
        ),
    }