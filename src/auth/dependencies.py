import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.exceptions import InvalidToken
from src.auth.service import decode_access_token
from src.database import get_db
from src.users.models import User

bearer_scheme = HTTPBearer()

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"}
)

async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    try:
        user_id = uuid.UUID(decode_access_token(credentials.credentials))
    except (InvalidToken, ValueError):
        raise _credentials_error

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_error

    return user