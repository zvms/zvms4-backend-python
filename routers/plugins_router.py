from fastapi import APIRouter
import json
import requests

from util.object_id import compulsory_temporary_token, get_current_user, validate_object_id

router = APIRouter()

@router.get('/dictionary/oxford/{word}')
def get_word_oxford(word: str):
    raise HTTPException(status_code=410, detail="Gone")

@router.get('/translate/deepl')
def translate_deepl(text: str, lang: str):
    raise HTTPException(status_code=410, detail="Gone")
