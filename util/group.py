from bson import ObjectId
from database import db

async def get_user_permissions(user: dict):
    """
    Get user's permissions
    """
    groups = user['group']
    permissions = []

    for group in groups:
        group = await db.zvms.groups.find_one({"_id": ObjectId(group)})
        for permission in group['permissions']:
            if permission not in permissions:
                permissions.append(permission)

    return permissions
