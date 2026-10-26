import secrets

from src.crypto.encryption.constants import TOKEN_BYTES


def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)
