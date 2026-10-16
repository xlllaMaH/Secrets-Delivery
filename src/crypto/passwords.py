import asyncio

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.config import settings

_ph = PasswordHasher()
_semaphore = asyncio.Semaphore(settings.HASH_CONCURRENCY)


async def hash_password(password: str) -> str:
    async with _semaphore:
        return await asyncio.to_thread(_ph.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    async with _semaphore:
        try:
            return await asyncio.to_thread(_ph.verify, password_hash, password)
        except VerifyMismatchError:
            return False
