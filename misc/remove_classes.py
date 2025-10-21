from bson import ObjectId

from database import connect_to_mongo, db


async def main():
    await connect_to_mongo()
    groups = (
        await db.zvms.get_collection("groups")
        .find({"name": {"$regex": "三"}})
        .to_list(None)
    )
    groups = [str(x["_id"]) for x in groups]
    users = (
        await db.zvms.get_collection("users")
        .find({"group": {"$in": groups}})
        .to_list(None)
    )
    users = [str(x["_id"]) for x in users]
    await db.zvms_new.get_collection("activity_members").delete_many(
        {"member": {"$in": users}}
    )
    await db.zvms.get_collection("logs").delete_many({"user": {"$in": users}})
    await db.zvms_new.get_collection("activities").update_many(
        {
            "creator": {"$in": users},
        },
        {"$set": {"creator": "65e6fa210edc81d012ec46d9"}},
    )
    await db.zvms.get_collection("users").delete_many({"group": {"$in": groups}})
    await db.zvms.get_collection("groups").delete_many({"name": {"$regex": "三"}})
    activities = await db.zvms_new.get_collection("activities").find({}).to_list(None)
    for activity in activities:
        members = await db.zvms_new.get_collection("activity_members").count_documents(
            {
                "activity": str(activity["_id"]),
            }
        )
        if members == 0:
            await db.zvms_new.get_collection("activities").delete_one(
                {
                    "_id": ObjectId(activity["_id"]),
                }
            )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
