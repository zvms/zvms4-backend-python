from typing import Optional
import bcrypt
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from fastapi import HTTPException
import jwt
import json
import datetime
from database import db
from bson import ObjectId
from bcrypt import checkpw, gensalt, hashpw
from Crypto.Hash import SHA256

from util.group import get_user_permissions


class Auth:
    password: str
    time: int


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def check_password(password, hashed):
    return bcrypt.checkpw(password.encode("utf-8"), hashed)


public_key = RSA.import_key(open("rsa_public_key.pem", "rb").read())
private_key = RSA.import_key(open("rsa_private_key.pem", "rb").read())
jwt_private_key = open("aes_key.txt", "r").read()


def rsa_encrypt(plaintext):
    cipher = PKCS1_OAEP.new(public_key, hashAlgo=SHA256)
    encrypt_text = cipher.encrypt(bytes(plaintext.encode("utf8")))
    return encrypt_text.hex()


def rsa_decrypt(ciphertext):
    cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA256)
    decrypt_text = cipher.decrypt(bytes.fromhex(ciphertext))
    return decrypt_text.decode("utf8")


def jwt_encode(
    id: str,
    permissions: list[str],
    type: Optional[str] = "long",
):
    duration = (
        datetime.timedelta(days=15)
        if type == "long"
        else datetime.timedelta(minutes=15)
    )
    payload = {
        "iss": "zvms",
        "exp": datetime.datetime.utcnow() + duration,
        "iat": datetime.datetime.utcnow(),
        "sub": id,
        "scope": (
            "access_token" if type == "long" else "temporary_token"
        ),  # Dangerous Zone Access needs temporary token, others need access token.
        "per": permissions,
        "jti": str(ObjectId()),
    }
    result = jwt.encode(payload, jwt_private_key, algorithm="HS256")
    return result


def jwt_decode(token):
    return jwt.decode(token, jwt_private_key, algorithms=["HS256"], verify=True)


async def get_renewed_password(id: str, credential: str):
    field = json.loads(rsa_decrypt(credential))
    time = field["time"]
    if time < datetime.datetime.now().timestamp() - 60:
        raise HTTPException(status_code=401, detail="Token expired")
    new_password = hashpw(bytes(field["password"], "utf-8"), gensalt())
    await db.zvms.users.update_one(
        {"_id": ObjectId(id)}, {"$set": {"password": new_password}}
    )


async def validate_by_cert(id: str, cert: str, type: Optional[str] = "long"):
    auth_field = json.loads(rsa_decrypt(cert))
    time = auth_field["time"]
    # in a minute
    if time < datetime.datetime.now().timestamp() - 60:
        raise HTTPException(status_code=401, detail="Token expired")
    founded = await db.zvms.users.find({"_id": ObjectId(id)}).to_list(None)
    if len(founded) == 0:
        raise HTTPException(status_code=404, detail="User not found")
    user = founded[0]
    if checkpw(
        bytes(auth_field["password"], "utf-8"), bytes(user["password"], "utf-8")
    ):
        return jwt_encode(id, await get_user_permissions(user), type=type)
    else:
        raise HTTPException(status_code=403, detail="Password incorrect")


async def get_hashed_password_by_cert(cert: str):
    auth_field = json.loads(rsa_decrypt(cert))
    time = auth_field["time"]
    # in a minute
    if time < datetime.datetime.now().timestamp() - 60:
        raise HTTPException(status_code=401, detail="Token expired")
    password = auth_field["password"]
    return hashpw(bytes(password, "utf-8"), gensalt()).decode("utf-8")


async def checkpwd(id: str, pwd: str):
    user = await db.zvms.users.find_one({"_id": ObjectId(id)})
    if checkpw(bytes(pwd, "utf-8"), bytes(user["password"], "utf-8")):
        return True
    return False
