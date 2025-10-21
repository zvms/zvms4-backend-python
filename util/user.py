from database import db
from utils import validate_object_id


async def get_user_name(id: str):
    try:
        user = await db.zvms.users.find_one(
            {"_id": validate_object_id(id)}, {"name": True}
        )
        return user["name"]
    except Exception:
        return "Unknown"
