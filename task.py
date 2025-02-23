from database import connect_to_mongo, db
from datetime import datetime
from routers.groups_router import get_groups, get_user_times_in_class
import pandas as pd
from tqdm import tqdm

async def main():
    await connect_to_mongo()

    results = []

    classes = await get_groups(page=1, perpage=60, type='class', user={
        "id": '',
        "per": ["admin", "student"]
    })

    for classid in tqdm(classes['data']):
        result = await get_user_times_in_class(str(classid['_id']), start='2024-06-30T16:00:00.000Z', end='2025-01-31T16:00:00.000Z', page=1, perpage=100, user={
            "id": '',
            "per": ["admin", "student"]
        })

        results.extend(result['data'])
    
    df = pd.DataFrame(results)

    df.to_csv('data.csv')

import asyncio

if __name__ == '__main__':
    asyncio.run(main())