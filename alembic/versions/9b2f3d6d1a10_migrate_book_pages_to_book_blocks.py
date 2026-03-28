"""migrate book_pages to book_blocks

Revision ID: 9b2f3d6d1a10
Revises: 15485cb70e1d
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b2f3d6d1a10"
down_revision: Union[str, None] = "15485cb70e1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    columns = [column["name"] for column in inspector.get_columns(table_name)]
    return column_name in columns


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    index_names = [index["name"] for index in inspector.get_indexes(table_name)]
    return index_name in index_names


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) book_pages -> book_blocks rename (if needed)
    if _table_exists(inspector, "book_pages") and not _table_exists(inspector, "book_blocks"):
        op.rename_table("book_pages", "book_blocks")
        inspector = sa.inspect(bind)

    # Fresh DB safety: if none exists, create target table
    if not _table_exists(inspector, "book_blocks"):
        op.create_table(
            "book_blocks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("book_id", sa.Integer(), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=False),
            sa.Column("block_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("vector_id", sa.String(length=64), nullable=True),
            sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("char_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_book_blocks_id"), "book_blocks", ["id"], unique=False)
        op.create_index(op.f("ix_book_blocks_book_id"), "book_blocks", ["book_id"], unique=False)
        op.create_index(op.f("ix_book_blocks_vector_id"), "book_blocks", ["vector_id"], unique=True)
        return

    # 2) Add new columns for block-based + vector mapping
    if not _column_exists(inspector, "book_blocks", "block_index"):
        op.add_column("book_blocks", sa.Column("block_index", sa.Integer(), nullable=False, server_default="0"))

    if not _column_exists(inspector, "book_blocks", "vector_id"):
        op.add_column("book_blocks", sa.Column("vector_id", sa.String(length=64), nullable=True))

    # 3) Ensure indexes for new model
    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "book_blocks", op.f("ix_book_blocks_vector_id")):
        op.create_index(op.f("ix_book_blocks_vector_id"), "book_blocks", ["vector_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "book_blocks"):
        return

    # Drop vector index/columns if present
    if _index_exists(inspector, "book_blocks", op.f("ix_book_blocks_vector_id")):
        op.drop_index(op.f("ix_book_blocks_vector_id"), table_name="book_blocks")

    inspector = sa.inspect(bind)
    if _column_exists(inspector, "book_blocks", "vector_id"):
        op.drop_column("book_blocks", "vector_id")

    inspector = sa.inspect(bind)
    if _column_exists(inspector, "book_blocks", "block_index"):
        op.drop_column("book_blocks", "block_index")

    # Rename back only if old table does not exist
    inspector = sa.inspect(bind)
    if _table_exists(inspector, "book_blocks") and not _table_exists(inspector, "book_pages"):
        op.rename_table("book_blocks", "book_pages")
