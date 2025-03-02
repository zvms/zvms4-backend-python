import uuid
from time import sleep
from typing import Dict
from fastapi import APIRouter, HTTPException, Depends
import tempfile
from typings.export import ExportFormat, ExportTask, ExportStatus, ExportVariant
from util.calculate import calculate_time
from fastapi.responses import FileResponse
from io import BytesIO
from util.object_id import get_current_user, validate_object_id
from datetime import datetime
from database import db
import pandas as pd
from fastapi import BackgroundTasks
from pydantic import BaseModel

task_store: Dict[str, ExportTask] = {}


class CreateExport(BaseModel):
    start: str = ''
    end: str = ''
    format: ExportFormat


router = APIRouter()

async def process_task(task_id: str):
    task = task_store.get(task_id)
    if not task:
        return
    task.task_start = datetime.now()
    task.status = ExportStatus.processing
    if task.variant == ExportVariant.time:
        result = []
        users = await db.zvms.users.find({}).to_list(None)
        for idx, user in enumerate(users):
            if task.export_start is not None and task.export_start is not None:
                user_time = await calculate_time(str(user['_id']), (task.export_start.isoformat(), task.export_end.isoformat()))
            else:
                user_time = await calculate_time(str(user['_id']))
                more_on_campus = min(round(max(user_time['off-campus'] - 15, 1) / 2, 0), 6.0)
                more_off_campus = min(round(max(user_time['on-campus'] - 25, 1) / 3, 0), 6.0)
                user_time['on-campus'] += more_on_campus
                user_time['off-campus'] += more_off_campus
            group = await db.zvms.groups.find_one(
                {"_id": {"$in": list(map(lambda x: validate_object_id(x), user['group']))}, "type": "class"})
            if group is None:
                continue
            doc = {
                '_id': str(user["_id"]),
                'name': user["name"],
                'id': str(user["id"]),
                'group': group['name'],
                'on-campus': user_time["on-campus"],
                'off-campus': user_time["off-campus"],
                'social-practice': user_time["social-practice"]
            }
            result.append(doc)
            task.percentage = (idx + 1) / len(users) * 100
            sleep(0.01)
        df = pd.DataFrame(result)
        task.result = df
        task.status = ExportStatus.completed


@router.post("/time")
async def export_time(
    properties: CreateExport,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user)
):
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail='Permission denied')
    task_id = str(uuid.uuid4())
    task = ExportTask(
        id=task_id,
        status=ExportStatus.pending,
        format=properties.format,
        variant=ExportVariant.time,
        export_start=datetime.fromisoformat(properties.start) if properties.start != '' else None,
        export_end=datetime.fromisoformat(properties.end) if properties.end != '' else None,
        task_start=datetime.now(),
        task_end=None,
        result=None
    )
    task_store[task_id] = task
    background_tasks.add_task(process_task, task_id)
    return {
        "code": 201,
        "status": "ok",
        "data": task_id
    }


@router.get("/{task_id}")
async def get_export(task_id: str):
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    result = task.model_dump()
    del result['result']
    return {
        "code": 200,
        "status": "ok",
        "data": result
    }

@router.get("/{task_id}/file")
async def get_export_file(task_id: str):
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != ExportStatus.completed:
        raise HTTPException(status_code=400, detail="Task not completed")
    buffer = BytesIO()
    with tempfile.NamedTemporaryFile(suffix=f'.{task.format.suffix()}', delete=False) as tmp:
        if task.format == ExportFormat.excel:
            task.result.to_excel(tmp.name, index_label=False)
        elif task.format == ExportFormat.csv:
            task.result.to_csv(tmp.name, index_label=False)
        elif task.format == ExportFormat.json:
            task.result.to_json(tmp.name)
        elif task.format == ExportFormat.latex:
            task.result.to_latex(tmp.name)
        elif task.format == ExportFormat.html:
            task.result.to_html(tmp.name)
        else:
            raise HTTPException(status_code=400, detail="Invalid format")
        buffer.write(tmp.read())
    return FileResponse(tmp.name, media_type=task.format.mime())


@router.get("")
async def get_export_list():
    result = []
    for task_id, task in task_store.items():
        result.append({
            "id": task_id,
            "status": task.status,
            "variant": task.variant,
            "format": task.format,
            "task_start": task.task_start,
            "task_end": task.task_end,
            "percentage": task.percentage
        })
    return {
        "code": 200,
        "status": "ok",
        "data": result
    }
