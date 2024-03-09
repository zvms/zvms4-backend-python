import os
import time
from fastapi import UploadFile, APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from util import image_process, image_storage
from utils import (
    compulsory_temporary_token,
    get_current_user,
    randomString,
    validate_object_id,
)
import config
from database import db

router = APIRouter()


@router.put("")
async def upload_image(file: UploadFile, user=Depends(get_current_user)):
    file_name = randomString() + ".jpg"
    path = os.path.join(config.UPLOAD_FOLDER, file_name)
    with open(path, "wb") as buffer:
        buffer.write(await file.read())
    image_process.compress(path, path, config.MAX_SIZE)
    file_id = image_storage.upload(path)
    if not file_id:
        raise HTTPException(status_code=500, detail="Image storage failed")
    timestamp = int(time.time())
    db.zvms.images.insert_one(
        {"id": file_id, "timestamp": timestamp, "uploader": user["id"]}
    )
    if os.path.exists(path):
        os.remove(path)
    return {
        "status": "ok",
        "code": 200,
        "data": file_id,
    }


@router.get("/{image_id}/data")
async def get_image(image_id: str):
    data = await db.zvms.images.find_one({"_id": validate_object_id(image_id)})
    image = image_storage.getBBImage(data['id'])
    if image.status_code != 200:
        raise HTTPException(status_code=image.status_code, detail=image.text)
    else:

        def generate():
            for chunk in image.iter_content(chunk_size=1024):
                yield chunk

        return StreamingResponse(generate(), media_type="image/jpeg")


@router.delete("/{image_id}")
async def delete_image(image_id: str, user=Depends(compulsory_temporary_token)):
    image = db.zvms.images.find_one({"id": image_id})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    image = await db.zvms.images.find_one({"_id": validate_object_id(image_id)})
    image_storage.remove(image['id'])
    await db.zvms.images.delete_one({"_id": validate_object_id(image["_id"])})
    return {"status": "ok", "code": 200}


@router.get("")
async def get_images(user=Depends(get_current_user), page: int = 1, perpage: int = 10):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if "admin" not in user["per"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    result = (
        await db.zvms.images.find()
        .sort("_id", -1)
        .skip(0 if page == -1 else (page - 1) * perpage)
        .limit(0 if page == -1 else perpage)
        .to_list(None if page == -1 else perpage)
    )
    for image in result:
        image["_id"] = str(image["_id"])
    return {"status": "ok", "code": 200, "data": result}


@router.get("/{file_id}")
async def get_image_info(file_id: str, user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    image = await db.zvms.images.find_one({"_id": validate_object_id(file_id)})
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    image["_id"] = str(image["_id"])
    return {"status": "ok", "code": 200, "data": image}
