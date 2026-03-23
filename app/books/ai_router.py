from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.dependencies import get_current_user
from app.users.models import User
from app.books import repository as book_repository
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
