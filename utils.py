from bson import ObjectId
from fastapi import HTTPException


def validate_object_id(id: str):
    try:
        _id = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Object ID")
    return _id
