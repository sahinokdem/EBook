from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_user
from app.users.models import User
from app.books import repository as book_repository
from app.books import page_repository
from app.core.vector_db import vector_db_service, gemini_rag_service


router = APIRouter(prefix="/books", tags=["AI"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=15)


class RetrievedBlock(BaseModel):
    vector_id: str
    score: float
    page_number: Optional[int] = None
    block_index: Optional[int] = None
    content: str


class AskResponse(BaseModel):
    book_id: int
    question: str
    answer: str
    retrieved_blocks: List[RetrievedBlock]


class TranslatePageRequest(BaseModel):
    target_lang: str = Field(default="tr", min_length=2, max_length=10)


class TranslatedBlockItem(BaseModel):
    block_id: int
    block_index: int
    translated_content: str
    from_cache: bool


class TranslatePageResponse(BaseModel):
    book_id: int
    page_number: int
    target_lang: str
    translated_blocks: List[TranslatedBlockItem]
    full_translation: str


@router.post("/{book_id}/ask", response_model=AskResponse)
def ask_book(
    book_id: int,
    payload: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = book_repository.get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    try:
        retrieved = vector_db_service.search_similar_blocks(
            query=payload.question,
            user_id=current_user.id,
            book_id=book_id,
            limit=payload.top_k,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Vector search unavailable: {exc}",
        ) from exc

    if not retrieved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No indexed blocks found for this book. Re-process the book first.",
        )

    try:
        answer = gemini_rag_service.answer(question=payload.question, context_blocks=retrieved)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"RAG generation failed: {exc}") from exc

    return AskResponse(
        book_id=book_id,
        question=payload.question,
        answer=answer,
        retrieved_blocks=[RetrievedBlock(**item) for item in retrieved],
    )


@router.post("/{book_id}/pages/{page_number}/translate", response_model=TranslatePageResponse)
def translate_page(
    book_id: int,
    page_number: int,
    payload: TranslatePageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book = book_repository.get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    blocks = page_repository.get_blocks_by_page(db, book_id, page_number)
    if not blocks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No blocks found for this page")

    translated_items: List[TranslatedBlockItem] = []
    for block in blocks:
        cached = page_repository.get_translated_block(db, block.id, payload.target_lang)
        if cached:
            translated_items.append(
                TranslatedBlockItem(
                    block_id=block.id,
                    block_index=block.block_index,
                    translated_content=cached.translated_content,
                    from_cache=True,
                )
            )
            continue

        context = page_repository.get_block_context(
            db,
            book_id=book_id,
            current_page=block.page_number,
            current_index=block.block_index,
        )

        try:
            translated = gemini_rag_service.translate_block_with_context(
                current_text=block.content,
                prev_text=context.prev_text,
                next_text=context.next_text,
                target_lang=payload.target_lang,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Translation failed for block {block.id}: {exc}",
            ) from exc

        page_repository.create_translated_block(
            db,
            block_id=block.id,
            target_lang=payload.target_lang,
            translated_content=translated,
        )

        translated_items.append(
            TranslatedBlockItem(
                block_id=block.id,
                block_index=block.block_index,
                translated_content=translated,
                from_cache=False,
            )
        )

    translated_items = sorted(translated_items, key=lambda item: item.block_index)
    full_translation = "\n\n".join([item.translated_content for item in translated_items])

    return TranslatePageResponse(
        book_id=book_id,
        page_number=page_number,
        target_lang=payload.target_lang,
        translated_blocks=translated_items,
        full_translation=full_translation,
    )
