from database import db
from typings.time import UserActivityTime
from util.calculate import calculate_user_time
from datetime import datetime


async def compute_time():
    """
    This function is a placeholder for removing data from the database.
    It should be implemented to remove specific data as needed.
    """
    await db.zvms_new.get_collection("time").delete_many({})
    users = await db.zvms.get_collection("users").find({}).to_list(None)
    updated_at = datetime.now()
    for user in users:
        user_id = str(user["_id"])
        time = await calculate_user_time(user_id, allow_cache=False)
        time_analysis = UserActivityTime(
            _id="",
            user=user_id,
            on_campus_raw=time["on-campus"],
            off_campus_raw=time["off-campus"],
            social_practice=time["social-practice"],
            updated_at=updated_at,
        )
        time_struct = time_analysis.model_dump()
        await db.zvms_new.get_collection("time").insert_one(time_struct)
