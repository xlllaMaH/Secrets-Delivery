from datetime import UTC, datetime, timedelta

from sqlalchemy import case, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.crypto.encryption.cipher import decrypt, encrypt
from src.crypto.encryption.exceptions import DecryptionError
from src.crypto.encryption.keys import decode_key, encode_key, generate_key
from src.crypto.encryption.tokens import generate_token
from src.notes.exceptions import NoteNotFound
from src.notes.models import Note
from src.notes.schemas import NoteCreate, NoteCreated
from src.users.models import User


async def create_note(db: AsyncSession, owner: User, data: NoteCreate) -> NoteCreated:
    key = generate_key()
    token = generate_token()

    note = Note(
        token=token,
        owner_id=owner.id,
        title=data.title,
        payload=encrypt(data.text.encode(), key, token.encode()),
        max_views=data.max_views,
        expires_at=datetime.now(UTC) + timedelta(hours=data.expires_in_hours),
    )
    db.add(note)
    await db.commit()

    return NoteCreated(
        token=token,
        key=encode_key(key),
        expires_at=note.expires_at,
        max_views=note.max_views,
    )


async def reveal_note(
    db: AsyncSession, token: str, encoded_key: str, viewer: User | None
) -> str:
    now = datetime.now(UTC)

    note = await db.scalar(select(Note).where(Note.token == token))
    if (
        note is None
        or note.payload is None
        or note.consumed_at is not None
        or note.archived_at is not None
        or note.expires_at <= now
    ):
        raise NoteNotFound

    try:
        text = decrypt(note.payload, decode_key(encoded_key), token.encode()).decode()
    except DecryptionError:
        raise NoteNotFound from None

    if viewer is not None and viewer.id == note.owner_id:
        return text

    is_last_view = Note.views_count + 1 >= Note.max_views
    claimed = await db.scalar(
        update(Note)
        .where(
            Note.id == note.id,
            Note.consumed_at.is_(None),
            Note.archived_at.is_(None),
            Note.expires_at > now,
            Note.views_count < Note.max_views,
        )
        .values(
            views_count=Note.views_count + 1,
            consumed_at=case((is_last_view, now), else_=None),
            payload=case((is_last_view, None), else_=Note.payload),
        )
        .returning(Note.id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()

    if claimed is None:
        raise NoteNotFound
    return text
