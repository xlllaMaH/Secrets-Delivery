import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.crypto.encryption.constants import KEY_SIZE, NONCE_SIZE, TAG_SIZE
from src.crypto.encryption.exceptions import DecryptionError


def _cipher(key: bytes) -> AESGCM:
    if len(key) != KEY_SIZE:
        raise ValueError(f"key must be {KEY_SIZE} bytes")
    return AESGCM(key)


def encrypt(data: bytes, key: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    return nonce + _cipher(key).encrypt(nonce, data, aad)


def decrypt(blob: bytes, key: bytes, aad: bytes) -> bytes:
    if len(blob) < NONCE_SIZE + TAG_SIZE:
        raise DecryptionError

    nonce, ciphertext = blob[:NONCE_SIZE], blob[NONCE_SIZE:]

    try:
        return _cipher(key).decrypt(nonce, ciphertext, aad)
    except InvalidTag:
        raise DecryptionError from None
