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

async def is_in_a_same_class(user: str, another_user: str):
    """
    Check if two users are in the same class
    """
    # Get user's groups and another_user's groups
    user_groups = await db.zvms.users.find_one({"_id": ObjectId(user)})['group']
    another_user_groups = await db.zvms.users.find_one({"_id": ObjectId(another_user)})['group']

    user_groups_info = []
    another_user_groups_info = []

    for group in user_groups:
        group = await db.zvms.groups.find_one({"_id": ObjectId(group)})
        if group['type'] == 'class':
            user_groups_info.append(group)

    for group in another_user_groups:
        group = await db.zvms.groups.find_one({"_id": ObjectId(group)})
        if group['type'] == 'class':
            another_user_groups_info.append(group)

    for user_group in user_groups_info:
        for another_user_group in another_user_groups_info:
            if user_group['_id'] == another_user_group['_id']:
                return True

    return False
