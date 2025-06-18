from io import BytesIO
from typing import Literal, cast

from bson import Binary, ObjectId
from routers.activities_v2_router import create_activity_v2
from typings.activity_v2 import Activity, ActivityMember
from fastapi import APIRouter, File, HTTPException, Depends, UploadFile
import copy
from typings.log import inject_log
from util.user import get_user_name
from util.object_id import get_current_user
from datetime import datetime
from database import db
import pandas as pd

from util.validation import validate_activity_name
from utils import validate_object_id

router = APIRouter()


@router.post("/activities")
async def upload_activity_excel(
    name: str,
    desc: str,
    payload: UploadFile = File(...),
    user=Depends(get_current_user),
    log=Depends(inject_log),
):
    """
    Upload activity excel
    """

    if not validate_activity_name(name):
        raise HTTPException(status_code=400, detail="Invalid activity name.")

    if (
        payload.content_type
        != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        and payload.content_type != "application/vnd.ms-excel"
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. You should upload an excel file",
        )

    expected_columns = [
        "_id",
        "Name",
        "ID",
        "Group",
        "On Campus",
        "Off Campus",
        "Social Practice",
    ]

    try:
        contents = await payload.read()

        await db.zvms.imports.insert_one(
            {
                "name": name,
                "filename": payload.filename,
                "description": desc,
                "user": user["id"],
                "date": datetime.now().isoformat(),
                "content": Binary(contents),
            }
        )

        filename = BytesIO(contents)

        sheet_names = pd.ExcelFile(filename).sheet_names

        # Read all sheets into a list of DataFrames
        dfs = [pd.read_excel(filename, sheet_name=sheet) for sheet in sheet_names]

        # Concatenate all DataFrames into one
        df = pd.concat(dfs, ignore_index=True)

        if df.columns.to_list() != expected_columns:
            raise HTTPException(status_code=400, detail="Invalid excel format")

        df.fillna(0.0)
        accepted_modes = ["On Campus", "Off Campus", "Social Practice"]

        log.with_text(f"User {await get_user_name(user['id'])} uploaded activity excel")
        await log.insert_log()

        info = Activity(
            _id="",
            type="hybrid",
            name=name,
            description=desc,
            date=datetime.now(),
            createdAt=datetime.now(),
            updatedAt=datetime.now(),
            creator=user["id"],
            status="effective",
            approver="authority",
            place="",
            origin="import",
            appointee=user["id"]
        )
        info_append = info.model_dump()
        inserted = await db.zvms_new.get_collection('activities').insert_one(info_append)
        activity_id = inserted.inserted_id

        for mode in accepted_modes:
            for idx, row in df.iterrows():
                if row[mode] != 0.0 and not pd.isna(row[mode]):
                    users = await db.zvms.users.find_one(
                        {"_id": validate_object_id(row["_id"])}
                    )
                    record_mode = mode.lower().replace(" ", "-")
                    if not record_mode in ["on-campus", "off-campus", "social-practice"]:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid mode: {mode}. Expected one of {accepted_modes}.",
                        )
                    record_mode = cast(Literal["on-campus", "off-campus", "social-practice"], record_mode)
                    if users is not None:
                        member = ActivityMember(
                            member=str(users['_id']),
                            activity=str(activity_id),
                            _id="",
                            status="effective",
                            mode=record_mode,
                            duration=row[mode],
                        )
                        member_append = member.model_dump()
                        await db.zvms_new.get_collection('activity_members').insert_one(member_append)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok", "code": 201}
