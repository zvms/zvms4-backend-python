from typing import Optional
from typings.group import Group
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from database import db
from pydantic import BaseModel

from util.calculate import calculate_time
from util.cert import check_password
from util.get_class import get_activities_related_to_user
import requests

from util.object_id import compulsory_temporary_token, get_current_user, validate_object_id

router = APIRouter()

@router.get('/dictionary/oxford/{word}')
def get_word_oxford(word: str):
    result = requests.get(f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}').json()
    return result
