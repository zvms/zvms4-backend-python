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

    if "monitor" in user.get("perm"):
        # If the user is a monitor, it should be in the same class
        user_class_id = await get_user_class(user["id"])
        if user_class_id in target_user.group:
            return True

    # If the user is the appointee, it's allowed to add member, but need to adjust the activity status to pending
    if user["id"] == target_activity.appointee:
        return "partial"

    return False


async def validate_update_permission(user: dict):
    """
    Validate if the user has permission to update an activity member.
    """
    return "admin" in user.get("perm") or "volunteer" in user.get("perm")
