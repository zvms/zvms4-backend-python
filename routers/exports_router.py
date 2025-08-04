import os
import uuid
from time import sleep
from fastapi import APIRouter, HTTPException, Depends, Request
import tempfile

from config import BASE_ON_CAMPUS, ON_TO_OFF_RATE, MAX_EXCEED_DISCOUNT, BASE_OFF_CAMPUS, OFF_TO_ON_RATE
from typings.export import ExportFormat, ExportTask, ExportStatus, ExportVariant
from util.calculate import calculate_user_time
from fastapi.responses import FileResponse
from io import BytesIO
import base64
import json
from util.object_id import get_current_user, validate_object_id, compulsory_temporary_token
from datetime import datetime
from database import db
import pandas as pd
from fastapi import BackgroundTasks
from pydantic import BaseModel


class CreateExport(BaseModel):
    start: str = ""
    end: str = ""
    format: ExportFormat
    allow_cache: bool = False
    include_description: bool = False

tokens = []


router = APIRouter()


async def process_task(task_id: str):
    task = await db.zvms.tasks.find_one({"id": uuid.UUID(task_id)})
    if not task:
        return
    await db.zvms.tasks.update_one(
        {"id": uuid.UUID(task_id)},
        {"$set": {"status": ExportStatus.processing, "task_start": datetime.now()}},
    )
    include_description = task.get("include_description", False)
    if task["variant"] == "time":
        result = []
        users = await db.zvms.users.find({}).to_list(None)
        for idx, user in enumerate(users):
            if task["export_start"] is not None and task["export_start"] is not None:
                user_time = await calculate_user_time(
                    str(user["_id"]),
                    task["export_start"],
                    task["export_end"],
                    attach_description=include_description,
                )
            else:
                user_time = await calculate_user_time(
                    str(user["_id"]), allow_cache=task["allow_cache"],
                    attach_description=include_description,
                )
            more_on_campus = min(
                round(max(user_time["off-campus"] - BASE_OFF_CAMPUS, 1) * OFF_TO_ON_RATE, 0), MAX_EXCEED_DISCOUNT
            )
            more_off_campus = min(
                round(max(user_time["on-campus"] - BASE_ON_CAMPUS, 1) * ON_TO_OFF_RATE, 0), MAX_EXCEED_DISCOUNT
            )
            user_time["on-campus"] += more_on_campus
            user_time["off-campus"] += more_off_campus
            group = await db.zvms.groups.find_one(
                {
                    "_id": {
                        "$in": list(map(lambda x: validate_object_id(x), user["group"]))
                    },
                    "type": "class",
                }
            )
            if group is None:
                continue
            doc = {
                "_id": str(user["_id"]),
                "Name": user["name"],
                "ID": str(user["id"]),
                "Group": group["name"],
                "On Campus": user_time["on-campus"],
                "Off Campus": user_time["off-campus"],
                "Social Practice": user_time["social-practice"],
                "Description": "" if not include_description else user_time.get("description", ""),
            }
            result.append(doc)
            task["percentage"] = (idx + 1) / len(users) * 100
            if idx % 20 == 19:
                await db.zvms.tasks.update_one(
                    {"id": uuid.UUID(task_id)},
                    {
                        "$set": {
                            "percentage": task["percentage"],
                        },
                        "$push": {"result": {"$each": result}},
                    },
                )
                result = []
                sleep(0.01)
        await db.zvms.tasks.update_one(
            {"id": uuid.UUID(task_id)},
            {
                "$set": {
                    "percentage": 100,
                    "status": ExportStatus.completed,
                    "task_end": datetime.now(),
                },
                "$push": {"result": {"$each": result}},
            },
        )
    elif task["variant"] == "users":
        result = []
        users = await db.zvms.users.find({}).to_list(None)
        for idx, user in enumerate(users):
            group = await db.zvms.groups.find_one(
                {
                    "_id": {
                        "$in": list(map(lambda x: validate_object_id(x), user["group"]))
                    },
                    "type": "class",
                }
            )
            doc = {
                "_id": str(user["_id"]),
                "Name": user["name"],
                "ID": str(user["id"]),
                "Group": group["name"],
                "On Campus": None,
                "Off Campus": None,
                "Social Practice": None,
            }
            result.append(doc)
            task["percentage"] = (idx + 1) / len(users) * 100
            if idx % 20 == 19:
                await db.zvms.tasks.update_one(
                    {"id": uuid.UUID(task_id)},
                    {
                        "$set": {
                            "percentage": task["percentage"],
                        },
                        "$push": {"result": {"$each": result}},
                    },
                )
                result = []
                sleep(0.01)
        await db.zvms.tasks.update_one(
            {"id": uuid.UUID(task_id)},
            {
                "$set": {
                    "percentage": 100,
                    "status": ExportStatus.completed,
                    "task_end": datetime.now(),
                },
                "$push": {"result": {"$each": result}},
            },
        )
    else:
        await db.zvms.tasks.update_one(
            {"id": uuid.UUID(task_id)},
            {
                "$set": {
                    "status": ExportStatus.failed,
                    "task_end": datetime.now(),
                    "errmsg": "Invalid variant",
                }
            },
        )


@router.post("/users")
async def export_users(
    background_tasks: BackgroundTasks, user=Depends(get_current_user)
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    task_id = uuid.uuid4()
    task = ExportTask(
        id=task_id,
        status=ExportStatus.pending,
        format=ExportFormat.excel,
        variant=ExportVariant.users,
        export_start=None,
        export_end=None,
        task_start=datetime.now(),
        task_end=None,
        result=[],
    )
    document = task.model_dump()
    document["variant"] = ExportVariant.users.value
    document["format"] = document["format"].value
    document["status"] = document["status"].value
    await db.zvms.tasks.insert_one(document)
    background_tasks.add_task(process_task, str(task_id))
    return {"code": 201, "status": "ok", "data": str(task_id)}


@router.post("/time")
async def export_time(
    properties: CreateExport,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    task_id = uuid.uuid4()
    task = ExportTask(
        id=task_id,
        status=ExportStatus.pending,
        format=properties.format,
        variant=ExportVariant.time,
        export_start=datetime.fromisoformat(properties.start)
        if properties.start != ""
        else None,
        export_end=datetime.fromisoformat(properties.end)
        if properties.end != ""
        else None,
        task_start=datetime.now(),
        task_end=None,
        result=[],
        allow_cache=properties.allow_cache,
        include_description=properties.include_description,
    )
    document = task.model_dump()
    document["variant"] = ExportVariant.time.value
    document["format"] = document["format"].value
    document["status"] = document["status"].value
    await db.zvms.tasks.insert_one(document)
    background_tasks.add_task(process_task, str(task_id))
    return {"code": 201, "status": "ok", "data": str(task_id)}


@router.get("/{task_id}")
async def get_export(task_id: str):
    task = await db.zvms.tasks.find_one({"id": uuid.UUID(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    del task["result"]
    task["_id"] = str(task["_id"])
    return {"code": 200, "status": "ok", "data": task}

@router.post("/reports")
async def request_download_reports(
    user=Depends(compulsory_temporary_token),
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    global tokens
    token_data = {
        'token': uuid.uuid4().hex,
        'granted_to': user['id'],
        'expires_at': datetime.now().timestamp() + 300  # 5 minutes
    }
    token_data_encoded = base64.b64encode(json.dumps(token_data).encode()).decode()
    tokens.append(token_data)
    return token_data_encoded

@router.get("/reports/download")
async def download_reports(
    request: Request,
    token: str,
):
    global tokens
    try:
        token_data = json.loads(base64.b64decode(token).decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token format")

    if not any(t['token'] == token_data['token'] for t in tokens):
        raise HTTPException(status_code=403, detail="Invalid or expired token")

    if datetime.now().timestamp() > token_data['expires_at']:
        raise HTTPException(status_code=403, detail="Token expired")

    # Remove the token after use
    tokens = [t for t in tokens if t['token'] != token_data['token']]

    # response to `export.tar.gz`, which is a tar.gz file containing all reports and already exists in the server
    file_path = "./data/export.tar.gz"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        file_path,
        media_type="application/gzip",
        filename="export.tar.gz",
        headers={
            "Content-Disposition": "attachment; filename=export.tar.gz"
        }
    )


@router.get("/{task_id}/file")
async def get_export_file(task_id: str, language: str = "en"):
    task = await db.zvms.tasks.find_one({"id": uuid.UUID(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed")
    buffer = BytesIO()
    with tempfile.NamedTemporaryFile(
        suffix=f'.{ExportFormat(task['format']).suffix()}', delete=False
    ) as tmp:
        result = pd.DataFrame(task["result"]).sort_values("_id")
        if language == "zh-CN":
            result.rename(columns={
                "_id": "数据库 ID",
                "Name": "姓名",
                "ID": "学号",
                "Group": "班级",
                "On Campus": "校内义工时长",
                "Off Campus": "校外义工时长",
                "Social Practice": "社会实践时长",
                "Description": "描述",
            }, inplace=True)
        if task["format"] == "excel":
            result.to_excel(tmp.name, index=False)
        elif task["format"] == "csv":
            result.to_csv(tmp.name, index=False)
        elif task["format"] == "json":
            result.to_json(tmp.name)
        elif task["format"] == "latex":
            result.to_latex(tmp.name)
        elif task["format"] == "html":
            result.to_html(tmp.name)
        else:
            raise HTTPException(status_code=400, detail="Invalid format")
        buffer.write(tmp.read())
        await db.zvms.tasks.delete_one({"id": uuid.UUID(task_id)})
    return FileResponse(tmp.name, media_type=ExportFormat(task["format"]).mime())


@router.get("")
async def get_export_list():
    result = []
    for task_id, task in enumerate(await db.zvms.tasks.find({}).to_list(None)):
        result.append(
            {
                "_id": str(task["_id"]),
                "id": task["id"],
                "status": task["status"],
                "variant": task["variant"],
                "format": task["format"],
                "task_start": task["task_start"],
                "task_end": task["task_end"],
                "percentage": task["percentage"],
            }
        )
    return {"code": 200, "status": "ok", "data": result}
