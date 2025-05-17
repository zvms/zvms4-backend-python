from fastapi import HTTPException
from typings.activity_v2 import Activity


async def validate_create_permission(user: dict, hybrid: bool):
    if "admin" or "volunteer" in user.get("perm"):
        return True
    if "monitor" in user.get("perm") and not hybrid:
        return "partial"
    raise HTTPException(status_code=403, detail="Permission denied")


async def validate_update_permission(user: dict, activity: Activity) -> bool:
    if "admin" in user.get("perm") or "volunteer" in user.get("perm"):
        return True
    if "monitor" in user.get("perm"):
        if activity.creator == str(user["id"]) or activity.appointee == str(user["id"]):
            return True
        else:
            raise HTTPException(status_code=403, detail="Permission denied")
    raise HTTPException(status_code=403, detail="Permission denied")
