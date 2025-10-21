import os
from collections import defaultdict
from typing import cast
import tarfile
import numpy as np
import pandas as pd
from datetime import datetime
from config import (
    BASE_OFF_CAMPUS,
    OFF_TO_ON_RATE,
    MAX_EXCEED_DISCOUNT,
    BASE_ON_CAMPUS,
    ON_TO_OFF_RATE,
    BASE_SOCIAL_PRACTICE,
)
from database import db
from util.calculate import calculate_user_time, time_with_origin
from util.statement import create_statement_from_kernel_data, TRANSLATIONS
from utils import validate_object_id


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


async def compute_ay_time():
    await db.zvms_new.get_collection("time_academic_year").delete_many({})
    users = await db.zvms.get_collection("users").find({}).to_list(None)
    now = datetime.now()
    ay = now.year if now.month >= 9 else now.year - 1
    soy = datetime.now().replace(
        month=8, day=1, year=ay, hour=0, minute=0, second=0, microsecond=0
    )
    eoy = datetime.now().replace(
        month=7, day=31, year=ay + 1, hour=23, minute=59, second=59, microsecond=999999
    )
    for user in users:
        user_id = str(user["_id"])
        entry = user_id[:4]
        result = await calculate_user_time(
            user_id, date_start=soy, date_end=eoy, allow_cache=False
        )
        await db.zvms_new.get_collection("time_academic_year").delete_many(
            {"user": user_id}
        )
        await db.zvms_new.get_collection("time_academic_year").insert_one(
            {
                "user": user_id,
                "entry": entry,
                "academic_year": ay,
                "start_of_year": soy,
                "end_of_year": eoy,
                **result,
            }
        )


async def generate_reports():
    classes = (
        await db.zvms.get_collection("groups").find({"type": "class"}).to_list(None)
    )
    await db.zvms_new.get_collection("daily_exports").delete_many({})
    db_data = await db.zvms_new.get_collection("daily_exports").insert_one(
        {"created_at": datetime.now(), "status": "processing", "data": []}
    )
    db_id = validate_object_id(db_data.inserted_id)
    if not os.path.exists("./export"):
        os.makedirs("./export")
    else:
        for item in os.listdir("./export"):
            item_path = os.path.join("./export", item)
            if os.path.isdir(item_path):
                for file in os.listdir(item_path):
                    file_path = os.path.join(item_path, file)
                    if file.endswith(".pdf"):
                        os.remove(file_path)
                os.rmdir(item_path)
    for class_id in classes:
        users = (
            await db.zvms.get_collection("users")
            .find({"group": str(class_id["_id"])})
            .to_list(None)
        )
        os.makedirs(f'./export/{class_id["name"]}', exist_ok=True)
        for user in users:
            user_id = str(user["id"])
            entry = int(user_id[:4])
            soy = datetime.now().replace(
                month=8, day=1, year=entry, hour=0, minute=0, second=0, microsecond=0
            )
            eoy = datetime.now().replace(
                month=7,
                day=31,
                year=entry + 3,
                hour=23,
                minute=59,
                second=59,
                microsecond=999999,
            )
            filename, spreadsheet = await create_statement_from_kernel_data(
                str(user["_id"]),
                (soy, eoy),
                filename=f'./export/{class_id['name']}/{user['id']}_{user["name"]}.pdf',
                language="zh",
            )
            await db.zvms_new.get_collection("daily_exports").update_one(
                {"_id": db_id},
                {
                    "$push": {
                        "data": {
                            **spreadsheet,
                            "filename": filename,
                        }
                    }
                },
            )
            print(
                f"Exported statement for {user['name']} in class {class_id['name']} (saved to {filename})."
            )
        print(f"Exported statements for class {class_id['name']}.")
    # Create a tar.gz archive of the export directory
    spreadsheet_items = await db.zvms_new.get_collection("daily_exports").find_one(
        {"_id": db_id}
    )
    spreadsheet_items = spreadsheet_items.get("data", [])
    df = pd.DataFrame(spreadsheet_items)
    df.rename(columns=TRANSLATIONS["zh"]["spreadsheet"], inplace=True)
    if os.path.exists("./export/summary.xlsx"):
        os.remove("./export/summary.xlsx")
    df.to_excel(f"./export/summary.xlsx", index=False)
    if os.path.exists("./data/export.tar.gz"):
        os.remove("./data/export.tar.gz")
    with tarfile.open("./data/export.tar.gz", "w:gz") as tar:
        tar.add("./export", arcname="export")
    return "./data/export.tar.gz"


def describe_percentile(items: np.ndarray, step: int, bound: float) -> dict[str, float]:
    """
    Calculate percentiles for a given array of items.

    :param items: A numpy array of numerical values.
    :param step: The step size for calculating percentiles.
    :param bound: A bound value to limit the maximum percentile value.
    :return: A dictionary containing the percentiles.
    """
    percentiles = {}
    for i in range(100, -1, -step):
        percentiles[f"{i}%"] = round(min(np.percentile(items, i).item(), bound), 1)
    # Deduplicate. If the value is the same, we only keep the last one (i.e., the biggest percentile).
    dictionary = defaultdict(float)
    for key, value in percentiles.items():
        dictionary[value] = key
    result = cast(dict[str, float], {v: k for k, v in dictionary.items()})
    return result


def describe_statistical_indicators(items: np.ndarray) -> dict[str, float]:
    """
    Calculate statistical indicators for a given array of items.

    :param items: A numpy array of numerical values.
    :return: A dictionary containing the statistical indicators.
    """
    return {
        "mean": np.mean(items).item(),
        "median": float(np.median(items)),
        "mode": float(pd.Series(items).mode().iloc[0]),
        "std": np.std(items).item(),
        "min": np.min(items).item(),
        "max": np.max(items).item(),
        "var": np.var(items).item(),
        "sum": np.sum(items).item(),
    }


def process_time_data(time_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process the time data DataFrame to calculate on-campus, off-campus, and social practice time.

    :param time_df: A DataFrame containing time data with columns 'on_campus_raw', 'off_campus_raw', and 'social_practice'.
    :return: A processed DataFrame with additional columns for on-campus, off-campus, and social practice time.
    """
    time_df.fillna(0, inplace=True)
    time_df["on-campus"] = time_df["on_campus_raw"] + np.round(
        (
            (time_df["off_campus_raw"] - BASE_OFF_CAMPUS).clip(lower=0) * OFF_TO_ON_RATE
        ).clip(lower=0, upper=MAX_EXCEED_DISCOUNT),
        1,
    )
    time_df["off-campus"] = time_df["off_campus_raw"] + np.round(
        (
            (time_df["on_campus_raw"] - BASE_ON_CAMPUS).clip(lower=0) * ON_TO_OFF_RATE
        ).clip(lower=0, upper=MAX_EXCEED_DISCOUNT),
        1,
    )
    time_df["social-practice"] = time_df["social_practice"]
    time_df["diff"] = (
        BASE_ON_CAMPUS
        + BASE_OFF_CAMPUS
        + BASE_SOCIAL_PRACTICE
        - time_df["on-campus"]
        - time_df["off-campus"]
        - time_df["social-practice"]
    )
    return time_df


def describe_df_percentile(
    df: pd.DataFrame, columns: list[str], step: int, bounds: list[float]
) -> dict[str, dict[str, float]]:
    """
    Calculate percentiles for a specific column in a DataFrame.

    :param df: A pandas DataFrame containing the data.
    :param columns: The column names for which to calculate percentiles.
    :param step: The step size for calculating percentiles.
    :param bounds: Bound values to limit the maximum percentile value.
    :return: A dictionary containing the percentiles for the specified column.
    """
    result = {}
    for column, bound in zip(columns, bounds):
        if column not in df.columns:
            raise ValueError(f"Column '{column}' does not exist in the DataFrame.")
        items = df[column].to_numpy()
        percentiles = describe_percentile(items, step, bound)
        result[column] = percentiles
    return result


def describe_df_statistical_indicators(
    df: pd.DataFrame, columns: list[str]
) -> dict[str, dict[str, float]]:
    """
    Calculate statistical indicators for specific columns in a DataFrame.

    :param df: A pandas DataFrame containing the data.
    :param columns: The column names for which to calculate statistical indicators.
    :return: A dictionary containing the statistical indicators for the specified columns.
    """
    result = {}
    for column in columns:
        if column not in df.columns:
            raise ValueError(f"Column '{column}' does not exist in the DataFrame.")
        items = df[column].to_numpy()
        indicators = describe_statistical_indicators(items)
        result[column] = indicators
    return result


async def compute_batch_origins():
    users_pipeline = [
        {
            "$group": {
                "_id": {"$substrCP": ["$id", 0, 4]},
                "originalIds": {"$push": "$_id"},
            }
        }
    ]
    grades = (
        await db.zvms.get_collection("users").aggregate(users_pipeline).to_list(None)
    )
    await db.zvms_new.get_collection("time_with_origin").delete_many({})
    await db.zvms_new.get_collection("time_with_origin_stat").delete_many({})
    groups = await db.zvms.get_collection("groups").find({"type": "class"}).to_list(None)
    for grade in grades:
        await time_with_origin("grade", grade["_id"])
        await time_with_origin("grade", grade["_id"], 20)
        await time_with_origin("grade", grade["_id"], 60)
        await time_with_origin("grade", grade["_id"], 80)
    for group in groups:
        await time_with_origin("group", str(group["_id"]))
        await time_with_origin("group", str(group["_id"]), 20)
        await time_with_origin("group", str(group["_id"]), 60)
        await time_with_origin("group", str(group["_id"]), 80)

async def compute_group_indicators():
    """
    This function computes group indicators based on the time data of users.
    """

    groups = (
        await db.zvms.get_collection("groups").find({"type": "class"}).to_list(None)
    )

    for group in groups:
        users = (
            await db.zvms.get_collection("users")
            .find({"group": str(group["_id"])})
            .to_list(None)
        )
        time_graph = (
            await db.zvms_new.get_collection("time")
            .find({"user": {"$in": [str(user["_id"]) for user in users]}})
            .to_list(None)
        )
        time_df = pd.DataFrame(time_graph)
        df = process_time_data(time_df)
        if df.empty:
            continue
        # Calculate percentiles and indicators
        percentiles = describe_df_percentile(
            df,
            ["on-campus", "off-campus", "social-practice"],
            step=1,
            bounds=[BASE_ON_CAMPUS, BASE_OFF_CAMPUS, BASE_SOCIAL_PRACTICE],
        )
        indicators = describe_df_statistical_indicators(
            df, ["on-campus", "off-campus", "social-practice"]
        )
        await db.zvms_new.get_collection("group_indicators").delete_many(
            {"group": str(group["_id"])}
        )
        await db.zvms_new.get_collection("group_indicators").insert_one(
            {
                "group": str(group["_id"]),
                "percentiles": percentiles,
                "indicators": indicators,
                "updated_at": datetime.now(),
            }
        )


async def compute_indicators():
    """
    We categorize users by their ID's starting 4 numbers (which indicate the registration year)
    Then we compute the time indicators for each grade, and classify them.
    Indicators include percentiles, compliance, and statistical indicators including mean, median, and mode.
    """
    await compute_group_indicators()
    users_pipeline = [
        {
            "$group": {
                "_id": {"$substrCP": ["$id", 0, 4]},
                "originalIds": {"$push": "$_id"},
            }
        }
    ]

    result = (
        await db.zvms.get_collection("users").aggregate(users_pipeline).to_list(None)
    )
    percentiles = {}  # Record<grade (str), dict<percentiles_name (str), value (float)>>
    indicators = {}  # Record<grade (str), dict<indicator_name (str), value (float)>>
    for item in result:
        grade = item["_id"]
        members = (
            await db.zvms_new.get_collection("time")
            .find(
                {"user": {"$in": [str(member) for member in item["originalIds"]]}},
                {"on_campus_raw": 1, "off_campus_raw": 1, "social_practice": 1},
            )
            .to_list(None)
        )
        df = pd.DataFrame(members)
        df = process_time_data(df)
        if df.empty:
            continue
        # Calculate percentiles and indicators
        percentiles[grade] = describe_df_percentile(
            df,
            ["on-campus", "off-campus", "social-practice"],
            step=1,
            bounds=[BASE_ON_CAMPUS, BASE_OFF_CAMPUS, BASE_SOCIAL_PRACTICE],
        )
        indicators[grade] = describe_df_statistical_indicators(
            df, ["on-campus", "off-campus", "social-practice"]
        )

    await db.zvms_new.get_collection("indicators").delete_many({})

    await db.zvms_new.get_collection("indicators").insert_one(
        {
            "percentiles": percentiles,
            "indicators": indicators,
            "updated_at": datetime.now(),
        }
    )


async def compute_tasks():
    await compute_time()
    await compute_ay_time()
    await compute_indicators()
    await compute_group_indicators()
    await compute_batch_origins()
