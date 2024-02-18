import bcrypt
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from fastapi import HTTPException
import jwt
import json
import datetime
from database import db
from bson import ObjectId
from bcrypt import checkpw
from Crypto.Hash import SHA256
import random


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


def jwt_encode(id: str, permissions: list[str]):
    payload = {
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15),
        "iat": datetime.datetime.utcnow(),
        "sub": id,
        "scope": "access_token",
        "type": "long-term",
        "per": permissions,
        "salt": random.randint(0, 2**31 - 1).to_bytes(4, "big").hex(),
    }
    result = jwt.encode(payload, jwt_private_key, algorithm="HS256")
    print(jwt_decode(result))
    return result


def jwt_decode(token):
    return jwt.decode(token, jwt_private_key, algorithms=["HS256"], verify=True)


async def validate_by_cert(id: str, cert: str):
    auth_field = json.loads(rsa_decrypt(cert))
    time = auth_field["time"]
    # in a minute
    if time < datetime.datetime.now().timestamp() - 60:
        print(time, datetime.datetime.now().timestamp() - 60)
        raise HTTPException(status_code=401, detail="Token expired")
    user = await db.zvms.users.find_one({"_id": ObjectId(id)})
    print(user, auth_field["password"], checkpw(bytes(auth_field["password"], "utf-8"), bytes(user["password"], "utf-8")))
    if checkpw(
        bytes(auth_field["password"], "utf-8"), bytes(user["password"], "utf-8")
    ):
        return jwt_encode(id, user["position"])
    raise HTTPException(status_code=401, detail="Password incorrect")

async def checkpwd(id: str, pwd: str):
    user = await db.zvms.users.find_one({"_id": ObjectId(id)})
    if checkpw(bytes(pwd, "utf-8"), bytes(user["password"], "utf-8")):
        return True
    return False
