from database import db
from util.title_modify import modify_title_automatically


async def regulate_titles():
    activities = await db.zvms_new.get_collection("activities").find({}).to_list(None)
    for activity in activities:
        new_title = modify_title_automatically(activity["name"])
        await db.zvms_new.get_collection("activities").update_one(
            {"_id": activity["_id"]}, {"$set": {"name": new_title}}
        )


async def remove_activities_with_zero_participants():
    """
    Remove activities that have no participants.
    """
    activities = await db.zvms_new.get_collection("activities").find({}).to_list(None)
    for activity in activities:
        count = await db.zvms_new.get_collection("activity_members").count_documents(
            {"activity": str(activity["_id"]), "status": "effective"}
        )
        if count == 0:
            await db.zvms_new.get_collection("activities").delete_one(
                {"_id": activity["_id"]}
            )

    refused = (
        await db.zvms_new.get_collection("activities")
        .find({"status": "refused"})
        .to_list(None)
    )

    for activity in refused:
        await db.zvms_new.get_collection("activity_members").delete_many(
            {"activity": str(activity["_id"])}
        )
        await db.zvms_new.get_collection("activities").delete_one(
            {"_id": activity["_id"]}
        )

    tests = (
        await db.zvms_new.get_collection("activities")
        .find({"title": {"$regex": "(调试|测试|Test|Debug)"}})
        .to_list(None)
    )

    for activity in tests:
        await db.zvms_new.get_collection("activity_members").delete_many(
            {"activity": str(activity["_id"])}
        )
        await db.zvms_new.get_collection("activities").delete_one(
            {"_id": activity["_id"]}
        )


async def wash_data():
    """
    Run all data washing tasks.
    """
    await regulate_titles()
    await remove_activities_with_zero_participants()
    # Add more data washing tasks here as needed
    print("Data washing completed.")
