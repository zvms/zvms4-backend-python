from typings.export import Export, ExportFormat, ExportStatus, ExportResponse
from database import connect_to_mongo, db
from util.time_export import calculate, json2csv, json2xlsx
from utils import get_current_user
from uuid import uuid4
import datetime
import asyncio

exports: list[ExportResponse] = []


async def export_time():
    await connect_to_mongo()
    users = await db.zvms.users.find().to_list(None)
    normal_activities = await db.zvms.activities.find(
        {"type": {"$ne": "special"}}
    ).to_list(None)
    special_activities = await db.zvms.activities.find(
        {"type": "special"}
    ).to_list(None)
    prize_activities = await db.zvms.activities.find(
        {"type": "prize"}
    ).to_list(None)
    groups = await db.zvms.groups.find().to_list(None)
    trophies = await db.zvms.trophies.find().to_list(None)
    prize_full = 10.0
    discount = False
    result = await calculate(
        users,
        normal_activities,
        special_activities,
        prize_activities,
        trophies,
        prize_full,
        discount,
        groups,
    )
    return result


import asyncio

asyncio.run(export_time())
