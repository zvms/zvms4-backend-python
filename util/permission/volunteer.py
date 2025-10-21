from fastapi import HTTPException
from typings.activity_v2 import Activity


async def validate_create_permission(user: dict, hybrid: bool):
    print(
        user.get("perm"), "admin" in user.get("perm"), "volunteer" in user.get("perm")
    )
    if "admin" in user.get("perm") or "volunteer" in user.get("perm"):
        return True
    
    raise HTTPException(status_code=403, detail="Permission denied")


async def validate_update_permission(user: dict, activity: Activity) -> bool:
    if "admin" in user.get("perm") or "volunteer" in user.get("perm"):
        return True
    
    raise HTTPException(status_code=403, detail="Permission denied")


async def validate_check_permission(
    user: dict, activity: Activity, strict: bool = False
) -> bool:
    if "admin" in user.get("perm") or "volunteer" in user.get("perm"):
        return True
    raise HTTPException(status_code=403, detail="Permission denied")
