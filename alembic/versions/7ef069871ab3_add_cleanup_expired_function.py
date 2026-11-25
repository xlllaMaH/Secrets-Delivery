"""add cleanup_expired function

Revision ID: 7ef069871ab3
Revises: bd35c8a90cc0
Create Date: 2026-11-25 22:55:23.089145

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '7ef069871ab3'
down_revision: Union[str, Sequence[str], None] = 'bd35c8a90cc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE FUNCTION cleanup_expired()
        RETURNS TABLE (wiped_notes integer, deleted_tokens integer)
        LANGUAGE plpgsql
        AS $$
        BEGIN
            UPDATE notes
            SET payload = NULL
            WHERE expires_at <= now() AND payload IS NOT NULL;
            GET DIAGNOSTICS wiped_notes = ROW_COUNT;

            DELETE FROM refresh_tokens
            WHERE expires_at <= now();
            GET DIAGNOSTICS deleted_tokens = ROW_COUNT;

            RETURN NEXT;
        END;
        $$

        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP FUNCTION cleanup_expired()")
