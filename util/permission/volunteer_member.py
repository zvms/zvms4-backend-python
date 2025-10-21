from typings.activity_v2 import Activity
from typings.user import User
from util.get_class import get_user_class


async def validate_create_permission(
    user: dict, target_user: User, target_activity: Activity
):
    """
    Validate if the user has permission to create an activity for the target user.
    """
    if "admin" in user.get("perm") or "volunteer" in user.get("perm"):
        return True

    return False


async def validate_update_permission(user: dict):
    """
    Validate if the user has permission to update an activity member.
    """
    return "admin" in user.get("perm") or "volunteer" in user.get("perm")
