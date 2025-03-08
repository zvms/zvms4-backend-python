import bcrypt
import motor.motor_asyncio
from bson import ObjectId
import asyncio
import os

async def insert_superadmin():
    """Insert a superadmin user with a fixed ObjectId in MongoDB."""
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client.zvms

    sagroup = {
        "_id": ObjectId('65e6fa211edc81d012ec41b9'),
        "name": "Admin",
        "description": "",
        "permissions": ["admin"],
        "type": "permission"
    }

    usergroup = {
        "_id": ObjectId('65e6fa211edc81d012ec41d0'),
        "name": "Class",
        "description": "",
        "permissions": ["student"],
        "type": "class"
    }

    superadmin_user = {
        "_id": ObjectId("65e6fa211edc81d012ec45e3"),
        "id": "19190810",
        "name": "Tester",
        "group": ["65e6fa211edc81d012ec41b9", "65e6fa211edc81d012ec45e3"],
        "sex": "unknown",
        "past": [],
        "password": bcrypt.hashpw(b'19190810', bcrypt.gensalt()).decode('utf-8')
    }
    if (await db.users.find_one({"_id": superadmin_user["_id"]})) is None:
        await db.users.insert_one(superadmin_user)
        print("Superadmin user inserted.")
    if (await db.groups.find_one({"_id": sagroup["_id"]})) is None:
        await db.groups.insert_one(sagroup)
        print("Admin group inserted.")
    if (await db.groups.find_one({"_id": usergroup["_id"]})) is None:
        await db.groups.insert_one(usergroup)
        print("Class group inserted.")
    # await client.close()

# Run the function asynchronously
asyncio.run(insert_superadmin())
