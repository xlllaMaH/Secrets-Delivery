from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import RefreshToken
from src.notes.models import Note


class CleanupStats(NamedTuple):
    notes: int
    tokens: int


async def wipe_expired_notes(db: AsyncSession, now: datetime) -> int:
    result = await db.execute(
        update(Note)
        .where(Note.expires_at <= now, Note.payload.is_not(None))
        .values(payload=None)
        .execution_options(synchronize_session=False)
    )

    return result.rowcount


async def delete_expired_refresh_tokens(db: AsyncSession, now: datetime) -> int:
    result = await db.execute(
        delete(RefreshToken)
        .where(RefreshToken.expires_at <= now)
        .execution_options(synchronize_session=False)
    )

    return result.rowcount


async def run_cleanup(db: AsyncSession) -> CleanupStats:
    now = datetime.now(UTC)
    notes = await wipe_expired_notes(db, now)
    tokens = await delete_expired_refresh_tokens(db, now)

    await db.commit()

    return CleanupStats(notes=notes, tokens=tokens)
