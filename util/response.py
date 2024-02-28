from enum import Enum


class Status(str, Enum):
    ok = "ok"
    error = "error"


def generate_response(status: Status, code: int, message: str, data):
    result = {
        "status": status,
        "code": code,
    }
    if message:
        result["message"] = message
    if data:
        result["data"] = data
