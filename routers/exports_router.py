import uuid
from time import sleep
from fastapi import APIRouter, HTTPException, Depends
import tempfile
from typings.export import ExportFormat, ExportTask, ExportStatus, ExportVariant
from util.calculate import calculate_user_time
from fastapi.responses import FileResponse
from io import BytesIO
from util.object_id import get_current_user, validate_object_id
from datetime import datetime
from database import db
import pandas as pd
from fastapi import BackgroundTasks
from pydantic import BaseModel


class CreateExport(BaseModel):
    start: str = ""
    end: str = ""
    format: ExportFormat
    allow_cache: bool = True


router = APIRouter()


async def process_task(task_id: str):
    task = await db.zvms.tasks.find_one({"id": uuid.UUID(task_id)})
    if not task:
        return
    await db.zvms.tasks.update_one(
        {"id": uuid.UUID(task_id)},
        {"$set": {"status": ExportStatus.processing, "task_start": datetime.now()}},
    )
    if task["variant"] == "time":
        result = []
        users = await db.zvms.users.find({}).to_list(None)
        for idx, user in enumerate(users):
            if task["export_start"] is not None and task["export_start"] is not None:
                user_time = await calculate_user_time(
                    str(user["_id"]),
                    task["export_start"],
                    task["export_end"],
                )
            else:
                user_time = await calculate_user_time(
                    str(user["_id"]), allow_cache=task["allow_cache"]
                )
            more_on_campus = min(
                round(max(user_time["off-campus"] - 15, 1) / 2, 0), 6.0
            )
            more_off_campus = min(
                round(max(user_time["on-campus"] - 25, 1) / 3, 0), 6.0
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


@router.get("/{task_id}/file")
async def get_export_file(task_id: str):
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
