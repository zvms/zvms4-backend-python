from datetime import datetime
from database import db
from routers.users_v2_router import get_user_time_statistics_v2
from typings.time import UserActivityTime
from util.object_id import validate_object_id
from bcrypt import checkpw
from tqdm import tqdm


async def describe_person(
    id: str
):
    demographics = await db.zvms.get_collection('users').find_one({'_id': validate_object_id(id)})
    time = await db.zvms_new.get_collection('time').find_one({'user': id})
    validated_time = UserActivityTime(
        on_campus_raw=time["on_campus_raw"],
        off_campus_raw=time["off_campus_raw"],
        social_practice=time["social_practice"],
        updated_at=datetime.now(),
        user=id,
        _id=''
    )
    time_ay = await db.zvms_new.get_collection('time_academic_year').find_one({'user': id})
    indicators = await get_user_time_statistics_v2(id, user={})
    time_with_origin = await db.zvms_new.get_collection('time_with_origin').find_one({'user': id})
    result = {
        **demographics,
        "password": checkpw(demographics['id'].encode('utf-8'), demographics['password'].encode('utf-8')),
        "time": validated_time.model_dump(),
        "time_ay": time_ay,
        "indicators": indicators,
        "time_with_origin": time_with_origin,
    }
    return result


async def describe_all(target: str):
    users = await db.zvms.get_collection("users").find({}).to_list(None)
    await db.zvms_new.get_collection('debug_descriptions').delete_many({})
    for user in tqdm(users):
        if not user['id'].startswith('2022'):
            continue
        result = await describe_person(str(user['_id']))
        await db.zvms_new.get_collection('debug_descriptions').insert_one({**result, 'fetched_at': datetime.now(), 'target': target})
    results = await db.zvms_new.get_collection('debug_descriptions').find({'target': target}).to_list(None)
    print(f"Saved {len(results)} records to {target}")
