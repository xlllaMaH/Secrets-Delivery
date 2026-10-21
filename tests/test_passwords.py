from src.crypto.passwords import hash_password, verify_password
from tests.conftest import EXISTING_PASSWORD


async def test_hash_is_argon2_and_not_plaintext():
    password = EXISTING_PASSWORD
    hashed = await hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert hashed != password


async def test_verify_correct_password():
    hashed = await hash_password(EXISTING_PASSWORD)

    assert await verify_password(EXISTING_PASSWORD, hashed) is True


async def test_verify_wrong_password():
    hashed = await hash_password(EXISTING_PASSWORD)

    assert await verify_password("wrong-password", hashed) is False


async def test_same_password_gives_different_hashed():
    fisrt_pass = await hash_password(EXISTING_PASSWORD)
    second_pass = await hash_password(EXISTING_PASSWORD)

    assert fisrt_pass != second_pass
