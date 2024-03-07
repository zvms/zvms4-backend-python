# backblaze 的上传 api 有点复杂（对于我来说），所以我专门另开了一个文件。

import os
import b2sdk.v2 as b2
import config
import time
from pathlib import Path
import requests

info = b2.InMemoryAccountInfo()
b2_api = b2.B2Api(info)
application_key_id = config.KEYID
application_key = config.APPKEY
b2_api.authorize_account("production", application_key_id, application_key)
bucket = b2_api.get_bucket_by_name("zvms4-imgbed")

def getRealname(filePath):
    if(filePath.find("/")):
        return filePath[filePath.find("/") + 1:]
    else:
        return filePath

def bbUpload(filePath):
    file_name = filePath
    local_file = Path(file_name).resolve()
    metadata = {"createdAt": str(time.time())}
    uploaded_file = bucket.upload_local_file(
        local_file=local_file,
        file_name=getRealname(filePath),
        file_infos=metadata,
    )
    return uploaded_file.id_
    # return (b2_api.get_download_url_for_fileid(uploaded_file.id_))

def bbDownload(fileid, authorization_token = b2_api.account_info.get_account_auth_token()):
    headers = None
    if authorization_token is not None:
         headers = {
             'Authorization': authorization_token
         }
    download_url = b2_api.get_download_url_for_fileid(fileid)
    download_url = config.CFURL + download_url[download_url.find(".com/") + 4:]
    response = requests.get(download_url, headers=headers)
    return response

def bbDelete(fileid):
    bucket.delete_file_version(fileid, getRealname(fileid))

if __name__ == '__main__':
    res = bbDownload("4_zd8ad465646ca80c885dc0611_f114a3c2c5d61f98c_d20240209_m053417_c005_v0501010_t0021_u01707456857078")
    print(res)
