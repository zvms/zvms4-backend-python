from fastapi import APIRouter
import json
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


@router.get('/translate/deepl')
def translate_deepl(text: str, lang: str):
    data = {'text': text, 'target_lang': lang}
    data = json.dumps(data)
    result = requests.post(f'http://127.0.0.1:1188/translate', data=data).json()
    return {
        'status': 'ok',
        'code': 200,
        'data': result
    }
