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


def jwt_encode(id: str):
    payload = {
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=60),
        "iat": datetime.datetime.utcnow(),
        "sub": id,
        "scope": "access_token",
        "type": "long-term",
    }
    return jwt.encode(payload, jwt_private_key, algorithm="HS256")


def jwt_decode(token):
    return jwt.decode(token, jwt_private_key, algorithms=["HS256"], verify=True)


def validate_by_cert(id: str, cert: str):
    auth_field = json.loads(rsa_decrypt(cert))
    time = auth_field["time"]
    # in a minute
    if time > datetime.datetime.now().timestamp() + 60:
        raise HTTPException(status_code=401, detail="Token expired")

    if checkpwd(id, auth_field["password"]):
        raise HTTPException(status_code=401, detail="Password incorrect")

    return jwt_encode(id)

def checkpwd(id: str, pwd: str):
    user = db.zvms.users.find_one({"_id": ObjectId(id)})
    if checkpw(bytes(pwd, 'utf-8'), user.get('password')):
        return True
    return False
