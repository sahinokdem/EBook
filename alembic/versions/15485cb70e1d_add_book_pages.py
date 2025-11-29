"""add book pages

Revision ID: 15485cb70e1d
Revises: c20877bf6295
Create Date: 2024-XX-XX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15485cb70e1d'
down_revision: Union[str, None] = 'c20877bf6295'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. ÖNCE enum type'ı oluştur
    bookstatus_enum = sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='bookstatus')
    bookstatus_enum.create(op.get_bind(), checkfirst=True)
    
    # 2. book_pages tablosunu oluştur
    op.create_table('book_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('char_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_book_pages_book_id'), 'book_pages', ['book_id'], unique=False)
    op.create_index(op.f('ix_book_pages_id'), 'book_pages', ['id'], unique=False)
    
    # 3. books tablosuna yeni kolonlar ekle
    op.add_column('books', sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='bookstatus'), nullable=False, server_default='PENDING'))
    op.add_column('books', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('books', sa.Column('total_pages', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_books_status'), 'books', ['status'], unique=False)
    
    # 4. file_size type değişikliği (BigInteger → Integer) - opsiyonel
    # op.alter_column('books', 'file_size', type_=sa.Integer())
    
    # 5. file_path kolonunu kaldır
    op.drop_column('books', 'file_path')


def downgrade() -> None:
    # 1. file_path'i geri ekle
    op.add_column('books', sa.Column('file_path', sa.VARCHAR(length=1000), nullable=True))
    
    # 2. Yeni kolonları kaldır
    op.drop_index(op.f('ix_books_status'), table_name='books')
    op.drop_column('books', 'total_pages')
    op.drop_column('books', 'error_message')
    op.drop_column('books', 'status')
    
    # 3. book_pages tablosunu sil
    op.drop_index(op.f('ix_book_pages_id'), table_name='book_pages')
    op.drop_index(op.f('ix_book_pages_book_id'), table_name='book_pages')
    op.drop_table('book_pages')
    
    # 4. Enum type'ı sil
    bookstatus_enum = sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='bookstatus')
    bookstatus_enum.drop(op.get_bind(), checkfirst=True)