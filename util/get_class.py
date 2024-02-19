from fastapi import HTTPException
from database import db
from utils import validate_object_id

def get_classid_by_code(code: int):
    codeid = str(code)
    if len(str(code)) == 7:
        codeid = '0' + str(code)

    if len(codeid) != 8:
        return None

    typeid = codeid[0:2]
    gradeid = codeid[2:4]
    classid = codeid[4:6]

    if gradeid == '00' or classid == '00':
        return None

    if typeid == '09':
        return 200000 + int(gradeid) * 100 + int(classid)
    else:
        return 200000 + int(gradeid) * 100 + 10 + int(classid)

async def get_classid_by_user_id(user_id: str):
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_id)})
    if not user:
        return None
    return get_classid_by_code(user['code'])

async def get_activities_related_to_user(user_oid: str):
    user = await db.zvms.users.find_one({"_id": validate_object_id(user_oid)})
    if not user:
        return HTTPException(status_code=404, detail="User not found")
    activities = await db.zvms.activities.find().to_list(1200)

    classid = get_classid_by_code(user['code'])

    user_map = []
    result = []

    users = await db.zvms.users.find().to_list(1200)

    for user in users:
        user['_id'] = str(user['_id'])
        user_map.append({
            'id': user['_id'],
            'code': user['code'],
            'classid': get_classid_by_code(user['code']),
        })

    def get_classid_by_user_id(user_id: str):
        for user in user_map:
            if user['id'] == user_id:
                return user['classid']
        return None

    for activity in activities:
        activity['_id'] = str(activity['_id'])
        flag_ = False
        if activity['creator'] == user_oid:
            flag_ = True
        for member in activity['members']:
            member_class = get_classid_by_user_id(member['_id'])
            if member_class == classid:
                flag_ = True
                break
        if not flag_:
            continue
        result.append(activity)
    return result
