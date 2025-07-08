from database import db
from util.calculate import calculate_user_time


async def compute_time():
    """
    This function is a placeholder for removing data from the database.
    It should be implemented to remove specific data as needed.
    """
    await db.zvms_new.get_collection("time").delete_many({})
    users = await db.zvms.get_collection("users").find({}).to_list(None)
    for user in users:
        user_id = str(user["_id"])
        await calculate_user_time(user_id, allow_cache=False)
