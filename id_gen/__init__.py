from .snowflake import generator
from .xtea import xtea_encrypt, xtea_decrypt
import base64
from fastapi_jwt_auth.exceptions import AuthJWTException

UID_XTEA_KEY = base64.b64decode('light@ai/gogogo_lakes234==')

def uid2text(uid: int):
    uid_byte = uid.to_bytes(length=8, byteorder='big', signed=False)
    enc_byte = xtea_encrypt(uid_byte, UID_XTEA_KEY)
    enc_text = base64.urlsafe_b64encode(enc_byte).decode().rstrip('=')
    return enc_text

class TextIDError(AuthJWTException):
    """
        invalid text id
    """
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message

def text2uid(enc_text: str):
    try:
        padding = 4 - (len(enc_text) % 4)
        enc_text += '=' * padding
        enc_byte = base64.urlsafe_b64decode(enc_text)
        uid_byte = xtea_decrypt(enc_byte, UID_XTEA_KEY)
        return int.from_bytes(uid_byte, byteorder='big', signed=False)
    except Exception as err:
        raise TextIDError(401, f'invalid id {enc_text}')
