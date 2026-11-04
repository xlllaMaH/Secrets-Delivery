import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, get_optional_user
from src.database import get_db
from src.notes.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from src.notes.exceptions import NoteNotFound
from src.notes.schemas import (
    NoteContent,
    NoteCreate,
    NoteCreated,
    NoteFilter,
    NotePage,
    NoteRead,
    RevealRequest,
)
from src.notes.service import (
    archive_note,
    create_note,
    get_note,
    list_note,
    reveal_note,
)
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


@router.post("/{token}/reveal", response_model=NoteContent)
async def reveal(
    token: str,
    data: RevealRequest,
    response: Response,
    viewer: Annotated[User | None, Depends(get_optional_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    response.headers["Cache-Control"] = "no-store"
    try:
        text = await reveal_note(db, token, data.key, viewer)
    except NoteNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from None
    return NoteContent(text=text)


@router.get("", response_model=NotePage)
async def list_my_notes(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    scope: Annotated[NoteFilter, Query(alias="status")] = NoteFilter.ACTIVE,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await list_note(db, user, scope, limit, offset)


@router.get("/{note_id}", response_model=NoteRead)
async def get_my_note(
    note_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await get_note(db, user, note_id)
    except NoteNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from None


@router.post("/{note_id}/archive", response_model=NoteRead)
async def archive(
    note_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await archive_note(db, user, note_id)
    except NoteNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        ) from None
