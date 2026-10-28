from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.crypto.encryption.cipher import encrypt
from src.crypto.encryption.keys import encode_key, generate_key
from src.crypto.encryption.tokens import generate_token
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
