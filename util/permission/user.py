from typing import Literal
from util.get_class import get_user_class
from database import db
from util.object_id import validate_object_id


async def validate_read_user_permission(
    user: dict, target_user: str, applied: Literal["volunteer", "club"]
):
    """
    Validate if the user has permission to read the target user's information.
    """
    if user["id"] == target_user:
        return True
    if "admin" in user.get("perm") or applied in user.get("perm"):
        return True
    if "monitor" in user.get("perm"):
        # If the user is a monitor, it should be in the same class
        user_class_id = await get_user_class(user["id"])
        target_classes = await db.zvms.get_collection("users").find_one(
            {"_id": validate_object_id(target_user)}
        )["group"]
        if user_class_id in target_classes:
            return True
    return False


async def validate_read_group_permission(
    user: dict, target_group: str, applied: Literal["volunteer", "club"]
):
    """
    Validate if the user has permission to read the target group's information.
    """
    if "admin" in user.get("perm") or applied in user.get("perm"):
        return True
    if "monitor" in user.get("perm"):
        # If the user is a monitor, it should be in the same class
        user_class_id = await get_user_class(user["id"])
        if user_class_id == target_group:
            return True
    return False
