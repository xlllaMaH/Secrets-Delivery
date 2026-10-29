from datetime import datetime

from pydantic import BaseModel, Field

from src.notes.constants import (
    DEFAULT_MAX_VIEWS,
    DEFAULT_TTL_HOURS,
    MAX_TEXT_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_TTL_HOURS,
    MAX_VIEWS_LIMIT,
    MIN_TTL_HOURS,
)


class NoteCreate(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    title: str | None = Field(default=None, max_length=MAX_TITLE_LENGTH)
    expires_in_hours: int = Field(
        default=DEFAULT_TTL_HOURS, ge=MIN_TTL_HOURS, le=MAX_TTL_HOURS
    )
    max_views: int = Field(default=DEFAULT_MAX_VIEWS, ge=1, le=MAX_VIEWS_LIMIT)


class NoteCreated(BaseModel):
    token: str
    key: str
    expires_at: datetime
    max_views: int


class RevealRequest(BaseModel):
    key: str = Field(min_length=1, max_length=128)


class NoteContent(BaseModel):
    text: str
