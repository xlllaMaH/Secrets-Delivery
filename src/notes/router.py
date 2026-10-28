from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.database import get_db
from src.notes.schemas import NoteCreate, NoteCreated
from src.notes.service import create_note
from src.users.models import User

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteCreated, status_code=status.HTTP_201_CREATED)
async def create(
    data: NoteCreate,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    response.headers["Cache-Control"] = "no-store"
    return await create_note(db, user, data)
