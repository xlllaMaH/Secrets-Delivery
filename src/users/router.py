from typing import Annotated

from fastapi import APIRouter, Depends

from src.auth.dependencies import get_current_user
from src.users.models import User
from src.users.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserRead)
async def read_me(user: Annotated[User, Depends(get_current_user)]):
    return user