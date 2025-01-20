from typing import Optional
from typings.group import Group
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from database import db
from pydantic import BaseModel
from PyDeepLX import PyDeepLX
from util.calculate import calculate_time
from util.cert import check_password
from util.get_class import get_activities_related_to_user
import requests

from util.object_id import compulsory_temporary_token, get_current_user, validate_object_id

router = APIRouter()

@router.get('/dictionary/oxford/{word}')
def get_word_oxford(word: str):
    result = requests.get(f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}').json()
    return {
        'status': 'ok',
        'code': 200,
        'data': result
    }


class TranslateRequest(BaseModel):
    text: str
    target_lang: str


@router.get('/translate/deepl')
def translate_deepl(text: str, lang: str):
    try:
        result = PyDeepLX.translate(text, lang, 3)
        return {
            'status': 'ok',
            'code': 200,
            'data': result
        }
    except PyDeepLX.TooManyRequestsException:
        return {
            'status': 'error',
            'code': 429,
            'detail': 'Too many requests'
        }
