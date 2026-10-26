import base64
import os

from src.crypto.encryption.constants import KEY_SIZE
from src.crypto.encryption.exceptions import DecryptionError


def generate_key() -> bytes:
    return os.urandom(KEY_SIZE)


def encode_key(key: bytes) -> str:
    return base64.urlsafe_b64encode(key).rstrip(b"=").decode("ascii")


def decode_key(encoded: str) -> bytes:
    padded = encoded + "=" * (-len(encoded) % 4)

    try:
        key = base64.b64decode(padded, altchars=b"-_", validate=True)
    except ValueError:
        raise DecryptionError from None

    if len(key) != KEY_SIZE:
        raise DecryptionError
    return key
