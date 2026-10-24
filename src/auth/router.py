from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.users.exceptions import UserAlreadyExists
from src.users.schemas import UserCreate, UserRead
from src.users.service import create_user

from src.auth.exceptions import InvalidCredentials
from src.auth.schemas import TokenPair, LoginRequest
from src.auth.service import login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        return await create_user(db, data)
    except UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username is already taken!",
        ) from None


@router.post("/login", response_model=TokenPair)
async def login_endpoint(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db,)]
):
    try:
        return await login(db, data.login, data.password)
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
            headers={"WWW-Authenticate": "Bearer"},
        ) from None