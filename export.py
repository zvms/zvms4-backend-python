from bson import ObjectId
from database import connect_to_mongo, db
import pandas as pd
from tqdm import tqdm

async def main():
    await connect_to_mongo()

    users = await db.zvms.users.find({}).to_list(None)

    data = []

    # data = {
    #     '_id': [],
    #     'ID': [],
    #     'Name': [],
    #     'Class ID': [],
    #     'On Campus': [],
    #     'Off Campus': [],
    #     'Social Practice': []
    # }

    for user in tqdm(users):
        class_id = await db.zvms.groups.find_one(
            {
                "_id": {"$in": [ObjectId(group) for group in user["group"]]},
                "type": "class"
            }
        )
        if class_id is None:
            class_id = None
        else:
            class_id = class_id["name"]
        data.append({
            '_id': str(user["_id"]),
            'ID': user["id"],
            'Name': user["name"],
            'Class ID': class_id,
            'On Campus': 0,
            'Off Campus': 0,
            'Social Practice': 0,
            'Grade': class_id[1] if class_id is not None else ''
        })

    df = pd.DataFrame(data)
    df.sort_values("ID", ascending=True)
    grouped = df.groupby('Grade', as_index=False)
    with pd.ExcelWriter("namelist.xlsx", engine="xlsxwriter") as writer:
        # Iterate over each group and write to a separate sheet
        for grade, group_df in grouped:
            group_df = group_df.sort_values(by=['Class ID', 'ID'], ascending=True)
            group_df = group_df.drop('Grade', axis=1)
            group_df.to_excel(writer, sheet_name=str(grade), index=False)

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
