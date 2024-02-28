from database import db
from typings.user import User

async def get_user_permissions(user: User):
    """
    Get user's permissions
    """
    groups = user.group

    permissions = []

    for group in groups:
        group = await db.zvms.groups.find_one({"_id": group})
        permissions.extend(group["permissions"])

    return permissions
