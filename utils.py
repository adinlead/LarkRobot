#!/usr/bin/env python3.8
import hashlib
import base64
from Crypto.Cipher import AES

from loguru import logger

LOG_FORMAT = "<green>{time:HH:mm:ss.SSS}</green> | " \
             "<level>{level: <8}</level> | " \
             "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

logger.add('log/system_{time:YYYY-MM-DD}.log', rotation='00:00', level="INFO", format=LOG_FORMAT)
logger.add('log/error_{time:YYYY-MM-DD}.log', rotation='00:00', level="ERROR", format=LOG_FORMAT)


def get_logger():
    return logger


class Obj(dict):
    def __init__(self, d):
        super().__init__()
        for a, b in d.items():
            if isinstance(b, (list, tuple)):
                setattr(self, a, [Obj(x) if isinstance(x, dict) else x for x in b])
            else:
                setattr(self, a, Obj(b) if isinstance(b, dict) else b)


def dict_2_obj(d: dict):
    return Obj(d)


class AESCipher(object):
    def __init__(self, key):
        self.bs = AES.block_size
        self.key = hashlib.sha256(AESCipher.str_to_bytes(key)).digest()

    @staticmethod
    def str_to_bytes(data):
        u_type = type(b"".decode("utf8"))
        if isinstance(data, u_type):
            return data.encode("utf8")
        return data

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1:])]

    def decrypt(self, enc):
        iv = enc[: AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:]))

    def decrypt_string(self, enc):
        enc = base64.b64decode(enc)
        return self.decrypt(enc).decode("utf8")


def singleton(cls):
    _instance = {}

    def _singleton(*args, **kwagrs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwagrs)
        return _instance[cls]

    return _singleton
