"""
Author: Vincent Young
Date: 2023-04-27 00:44:01
LastEditors: Vincent Young
LastEditTime: 2023-05-21 03:58:18
FilePath: /PyDeepLX/PyDeepLX/PyDeepLX.py
Telegram: https://t.me/missuo

Copyright © 2023 by Vincent, All Rights Reserved.
"""
import random
import time
import json
import requests

deeplAPI = "https://www2.deepl.com/jsonrpc"
headers = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "x-app-os-name": "iOS",
    "x-app-os-version": "16.3.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "x-app-device": "iPhone13,2",
    "User-Agent": "DeepL-iOS/2.9.1 iOS 16.3.0 (iPhone13,2)",
    "x-app-build": "510265",
    "x-app-version": "2.9.1",
    "Connection": "keep-alive",
}

def get_i_count(translateText) -> int:
    return translateText.count("i")


def get_random_number() -> int:
    random.seed(time.time())
    num = random.randint(8300000, 8399998)
    return num * 1000


def get_timestamp(iCount: int) -> int:
    ts = int(time.time() * 1000)

    if iCount == 0:
        return ts

    iCount += 1
    return ts - ts % iCount + iCount


def translate(
    text,
    source_lang="auto",
    target_lang="en",
    number_alternative=0,
    print_result=False,
):
    i_count = get_i_count(text)
    id = get_random_number()

    number_alternative = max(min(3, number_alternative), 0)

    post_data = {
        "jsonrpc": "2.0",
        "method": "LMT_handle_texts",
        "id": id,
        "params": {
            "texts": [{"text": text, "requestAlternatives": number_alternative}],
            "splitting": "newlines",
            "lang": {
                "source_lang_user_selected": source_lang,
                "target_lang": target_lang,
            },
            "timestamp": get_timestamp(i_count),
            "commonJobParams": {
                "wasSpoken": False,
                "transcribe_as": "",
            },
        },
    }
    post_data_str = json.dumps(post_data, ensure_ascii=False)

    if (id + 5) % 29 == 0 or (id + 3) % 13 == 0:
        post_data_str = post_data_str.replace('"method":"', '"method" : "', -1)
    else:
        post_data_str = post_data_str.replace('"method":"', '"method": "', -1)

    resp = requests.post(url=deeplAPI, data=post_data_str, headers=headers)
    resp_status_code = resp.status_code

    if resp_status_code != 200:
        return {
            'status': 'error',
            'code': resp_status_code,
            'detail': 'Request failed' + ': Too many requests.' if resp_status_code == 429 else ''
        }

    resp_text = resp.text
    resp_json = json.loads(resp_text)

    if number_alternative <= 1:
        target_text = resp_json["result"]["texts"][0]["text"]
        if print_result:
            print(target_text)
        return target_text

    target_text_array = []
    for item in resp_json["result"]["texts"][0]["alternatives"]:
        target_text_array.append(item["text"])
        if print_result:
            print(item["text"])

    return {
        'status': 'ok',
        'code': 200,
        'data': target_text_array
    }
