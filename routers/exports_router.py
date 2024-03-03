from typings.export import Export, ExportFormat, ExportStatus, ExportResponse
from fastapi import APIRouter, Depends, HTTPException, Response
from bson import ObjectId
from database import connect_to_mongo, db
from util.time_export import calculate, json2csv, json2xlsx
from utils import get_current_user
from uuid import uuid4
import datetime
import asyncio

router = APIRouter()

exports: list[ExportResponse] = []

lock = asyncio.Lock()


async def export_time(export: Export, id: str):
    if export.start is not None and export.end is not None:
        start = datetime.datetime.fromisoformat(export.start)
        end = datetime.datetime.fromisoformat(export.end)
    users = await db.zvms.users.find().to_list(None)
    timequery = (
        {"$gte": start, "$lte": end} if start is not None and end is not None else {}
    )
    normal_activities = await db.zvms.activities.find(
        {"type": {"$ne": "special"}, "date": timequery}
    ).to_list(None)
    special_activities = await db.zvms.activities.find(
        {"type": "special", "date": timequery}
    ).to_list(None)
    prize_activities = await db.zvms.activities.find(
        {"type": "prize", "date": timequery}
    ).to_list(None)
    groups = await db.zvms.groups.find().to_list(None)
    trophies = await db.zvms.trophies.find({"time": timequery}).to_list(None)
    prize_full = 10.0
    discount = False
    result = await calculate(
        users,
        normal_activities,
        special_activities,
        prize_activities,
        trophies,
        prize_full,
        discount,
        groups,
    )
    if export.format == ExportFormat.json:
        return Response(
            content=result,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=time.json"},
        )
    elif export.format == ExportFormat.csv:
        result = json2csv(result)
    elif export.format == ExportFormat.xlsx:
        result = json2xlsx(result)
    async with lock:
        for exportion in exports:
            if exportion.id == id:
                exportion.status = ExportStatus.completed
                exportion.data = result
                break


@router.get("")
async def get_exports(current_user: dict = Depends(get_current_user)):
    if "admin" not in current_user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    return {"status": "ok", "code": 200, "data": [export.id for export in exports]}


@router.post("")
async def create_export(export: Export, current_user: dict = Depends(get_current_user)):
    # if "admin" not in current_user["per"] or "inspector" not in current_user["per"]:
    # raise HTTPException(status_code=403, detail="Permission denied")
    if export.collection != "time":
        raise HTTPException(status_code=400, detail="Collection export unsupported")
    id = str(uuid4())
    print(f"Exporting time data to {export.format} with id {id}...")
    exports.append(
        ExportResponse(
            id=id,
            status=ExportStatus.pending,
            data=None,
            url="",
            error=None,
            format=export.format,
        )
    )
    await export_time(export, id)
    return {"status": "ok", "code": 201, "data": id}


@router.get("/{export_id}")
async def get_export(export_id: str):
    for export in exports:
        if export.id == export_id:
            result = {"status": "ok", "code": 200, "data": export}
            if export.status == ExportStatus.completed:
                exports.remove(export)
            return result
    raise HTTPException(status_code=404, detail="Export not found")


@router.get("/{export_id}/download")
async def download_export(export_id: str):
    for export in exports:
        if export.id == export_id:
            if export.status != ExportStatus.completed:
                raise HTTPException(status_code=404, detail="Export not found")
            if export.format == ExportFormat.json:
                return {"status": "ok", "code": 200, "data": export.data}
