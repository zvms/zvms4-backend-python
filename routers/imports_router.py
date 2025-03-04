from io import BytesIO
from bson import Binary

from routers.activities_router import create_activity
from typings.activity import (
    Activity,
    ActivityMember,
    ActivityMode,
    ActivityStatus,
    ActivityType,
    MemberActivityStatus,
    SpecialActivityClassify, Special,
)
from fastapi import APIRouter, File, HTTPException, Depends, UploadFile
import copy
from typings.log import inject_log
from util.user import get_user_name
from util.object_id import get_current_user
from datetime import datetime
from database import db
import pandas as pd

router = APIRouter()

@router.post("/activity")
async def upload_activity_excel(name: str, desc: str, payload: UploadFile = File(...), user=Depends(get_current_user),
                                log=Depends(inject_log)):
    """
    Upload activity excel
    """

    expected_columns = ['_id', 'ID', 'Name', 'Class ID', 'On Campus', 'Off Campus', 'Social Practice']

    try:
        contents = await payload.read()

        await db.zvms.imports.insert_one({
            "name": name,
            "filename": payload.filename,
            "description": desc,
            "user": user['id'],
            "date": datetime.now().isoformat(),
            "content": Binary(contents)
        })

        filename = BytesIO(contents)

        sheet_names = pd.ExcelFile(filename).sheet_names

        # Read all sheets into a list of DataFrames
        dfs = [pd.read_excel(filename, sheet_name=sheet) for sheet in sheet_names]

        # Concatenate all DataFrames into one
        df = pd.concat(dfs, ignore_index=True)

        if df.columns.to_list() != expected_columns:
            raise HTTPException(status_code=400, detail="Invalid excel format")

        df.fillna(0.0)
        accepted_modes = ['On Campus', 'Off Campus', 'Social Practice']

        info = Activity(_id='', type=ActivityType.special, name=name, description=desc, members=[], registration=None,
                        date=datetime.now().isoformat(), createdAt=datetime.now().isoformat(),
                        updatedAt=datetime.now().isoformat(), creator=user['id'], status=ActivityStatus.effective,
                        special=Special(classify=SpecialActivityClassify.import_), approver='authority')

        for mode in accepted_modes:
            template = copy.deepcopy(info)
            template.name += ' | Mode: ' + mode
            for idx, row in df.iterrows():
                if row[mode] != 0.0 and not pd.isna(row[mode]):
                    user = await db.zvms.users.find_one({"_id": validate_object_id(row['_id'])})
                    if user is not None:
                        template.members.append(ActivityMember(_id=row['_id'], id=row['_id'], status=MemberActivityStatus.effective,
                                                               mode=ActivityMode(mode.replace(' ', '-').lower()),
                                                               duration=row[mode]))
            if len(user) != 0:
                await create_activity(template, user=user, log=log)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    log.with_text(f"User {await get_user_name(user['id'])} uploaded activity excel")
    await log.insert_log()

    return {"status": "ok", "code": 201}
