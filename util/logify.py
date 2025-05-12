from bson import ObjectId
from fastapi import Depends, Request
from enum import Enum
from json import dumps
from database import db


def get_client_ip(request: Request) -> str:
    """
    Get client IP address
    """
    if "X-Forwarded-For" in request.headers:
        return request.headers["X-Forwarded-For"]
    return request.client.host


def get_client_clarity_user_id(request: Request) -> str:
    """
    Get client clarity user id
    """
    # Clarity User ID is stored in the cookie, with `_clck` as the key, whose content is the substring before content `%7C`
    if "_clck" in request.cookies:
        return request.cookies["_clck"].split("%7C")[0]
    if "Clarity-ID" in request.headers:
        return request.headers["Clarity-ID"]
    return ""


def binding_user_credentials(request: Request) -> dict:
    """
    Get user credentials
    """
    return {
        "clarity_id": get_client_clarity_user_id(request),
        "ip": get_client_ip(request),
    }
