import pytest

from src.crypto.encryption.constants import KEY_SIZE
from src.crypto.encryption.exceptions import DecryptionError
from src.crypto.encryption.keys import decode_key, encode_key, generate_key


def test_generate_key_has_expected_size():
    assert len(generate_key()) == KEY_SIZE


def test_generate_key_is_random():
    assert generate_key() != generate_key()


def test_encode_decode_roundtrip():
    key = generate_key()

    assert decode_key(encode_key(key)) == key


def test_encoded_key_has_no_padding_and_is_url_safe():
    encoded = encode_key(generate_key())

    assert len(encoded) == 43
    assert "=" not in encoded
    assert all(char.isalnum() or char in "-_" for char in encoded)


@pytest.mark.parametrize(
    "encoded",
    [
        "",
        "not base64 !!!",
        "abc",
        "ключ" * 11,
        encode_key(b"too short"),
        encode_key(b"x" * (KEY_SIZE + 1)),
        encode_key(b"x" * KEY_SIZE) + "!!",
    ],
    ids=[
        "empty",
        "not_base64",
        "too_short_text",
        "non_ascii",
        "short_key",
        "long_key",
        "valid_key_with_junk",
    ],
)
def test_decode_key_rejects_invalid_values(encoded):
    with pytest.raises(DecryptionError):
        decode_key(encoded)
