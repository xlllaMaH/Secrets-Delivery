import os

import pytest

from src.crypto.encryption.cipher import decrypt, encrypt
from src.crypto.encryption.constants import KEY_SIZE, NONCE_SIZE, TAG_SIZE
from src.crypto.encryption.exceptions import DecryptionError
from src.crypto.encryption.keys import generate_key

AAD = b"token-123"


def flip_byte(data: bytes, index: int) -> bytes:
    changed = bytearray(data)
    changed[index] ^= 1
    return bytes(changed)


@pytest.mark.parametrize(
    "data",
    [
        b"secret",
        "секрет 🔐".encode(),
        b"",
        b"\x00\xff" * 1000,
        b"x" * 1_000_000,
    ],
    ids=["ascii", "unicode", "empty", "binary", "one_megabyte"],
)
def test_encrypt_decrypt_roundtrip(data):
    key = generate_key()

    assert decrypt(encrypt(data, key, AAD), key, AAD) == data


def test_blob_layout_is_nonce_ciphertext_tag():
    data = b"secret"

    blob = encrypt(data, generate_key(), AAD)

    assert len(blob) == NONCE_SIZE + len(data) + TAG_SIZE


def test_blob_does_not_contain_plaintext():
    data = b"very-recognizable-plaintext"

    blob = encrypt(data, generate_key(), AAD)

    assert data not in blob


def test_each_encryption_uses_new_nonce():
    key = generate_key()

    first = encrypt(b"secret", key, AAD)
    second = encrypt(b"secret", key, AAD)

    assert first != second
    assert first[:NONCE_SIZE] != second[:NONCE_SIZE]


def test_decrypt_with_wrong_key():
    blob = encrypt(b"secret", generate_key(), AAD)

    with pytest.raises(DecryptionError):
        decrypt(blob, generate_key(), AAD)


def test_decrypt_with_wrong_aad():
    key = generate_key()
    blob = encrypt(b"secret", key, AAD)

    with pytest.raises(DecryptionError):
        decrypt(blob, key, b"another-token")


@pytest.mark.parametrize(
    "index",
    [0, NONCE_SIZE, -1],
    ids=["nonce", "ciphertext", "tag"],
)
def test_decrypt_tampered_blob(index):
    key = generate_key()
    blob = encrypt(b"secret", key, AAD)

    with pytest.raises(DecryptionError):
        decrypt(flip_byte(blob, index), key, AAD)


@pytest.mark.parametrize(
    "length",
    [0, 5, NONCE_SIZE, NONCE_SIZE + TAG_SIZE - 1],
    ids=["empty", "five_bytes", "only_nonce", "one_byte_short_of_minimum"],
)
def test_decrypt_too_short_blob(length):
    key = generate_key()
    blob = encrypt(b"secret", key, AAD)

    with pytest.raises(DecryptionError):
        decrypt(blob[:length], key, AAD)


def test_decrypt_truncated_blob():
    key = generate_key()
    blob = encrypt(b"secret", key, AAD)

    with pytest.raises(DecryptionError):
        decrypt(blob[:-1], key, AAD)


def test_decrypt_random_garbage():
    with pytest.raises(DecryptionError):
        decrypt(os.urandom(100), generate_key(), AAD)


@pytest.mark.parametrize("size", [0, 16, 24, KEY_SIZE - 1, KEY_SIZE + 1])
def test_encrypt_rejects_wrong_key_size(size):
    with pytest.raises(ValueError):
        encrypt(b"secret", os.urandom(size), AAD)


def test_decrypt_rejects_wrong_key_size():
    blob = encrypt(b"secret", generate_key(), AAD)

    with pytest.raises(ValueError):
        decrypt(blob, os.urandom(16), AAD)
