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
    user_group = await db.zvms.users.find_one({"_id": ObjectId(user)})
    user_group = user_group['group']
    another_group = await db.zvms.users.find_one({"_id": ObjectId(another_user)})
    another_group = another_group['group']

    user_group = [ObjectId(group) for group in user_group]
    another_group = [ObjectId(group) for group in another_group]

    user_group = await db.zvms.groups.find({
        "_id": {
            "$in": user_group
        },
        "type": "class"
    }).to_list(1)

    another_group = await db.zvms.groups.find({
        "_id": {
            "$in": another_group
        },
        "type": "class"
    }).to_list(1)

    if user_group and another_group:
        if user_group[0]['_id'] == another_group[0]['_id']:
            return True
        else:
            return False
