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
import json
import re
import time

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


class SummarizePageRequest(BaseModel):
    target_lang: str = Field(default="tr", min_length=2, max_length=10)


class SummarizePageResponse(BaseModel):
    book_id: int
    page_number: int
    target_lang: str
    summary: str


class SummarizeRequest(BaseModel):
    target_lang: str = Field(default="tr", min_length=2, max_length=10)
    start_page: Optional[int] = Field(default=None, ge=1)
    end_page: Optional[int] = Field(default=None, ge=1)


class SummarizeResponse(BaseModel):
    book_id: int
    target_lang: str
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    summary: str


def filter_glossary_for_text(glossary: dict, current_text: str) -> dict:
    if not glossary or not current_text:
        return {}
    filtered_dict = {}
    for term, explanation in glossary.items():
        if re.search(r'\b' + re.escape(term) + r'\b', current_text, re.IGNORECASE):
            filtered_dict[term] = explanation
    return filtered_dict


def chunk_text(text: str, max_chars: int = 15000) -> List[str]:
    """
    Metni word boundary'lere göre parçalara ayır.
    Her parça max_chars karakterden daha az olacak, fakat word'ü kesmeyecek.
    
    Args:
        text: Bölünecek metin
        max_chars: Maksimum karakter sayısı (sözcük sınırında kırılır)
    
    Returns:
        Parçalanmış metin listesi
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Paragrafları ayırarak başla (\n\n ile)
    paragraphs = text.split("\n\n")
    
    for para in paragraphs:
        if not para.strip():
            continue
        
        # Paragraf max_chars'dan küçükse, direkt ekle
        if len(current_chunk) + len(para) + 2 <= max_chars:  # +2 for "\n\n"
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            # Paragraf çok büyükse, cümle cümle böl
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # Paragrafı cümlelere ayır (basit regex)
            sentences = re.split(r'(?<=[.!?])\s+', para)
            temp_chunk = ""
            
            for sent in sentences:
                if not sent.strip():
                    continue
                if len(temp_chunk) + len(sent) + 1 <= max_chars:  # +1 for space
                    if temp_chunk:
                        temp_chunk += " " + sent
                    else:
                        temp_chunk = sent
                else:
                    if temp_chunk:
                        chunks.append(temp_chunk)
                    temp_chunk = sent
            
            if temp_chunk:
                current_chunk = temp_chunk
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return [c.strip() for c in chunks if c.strip()]

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

    # DB'den sözlüğü çek
    raw_glossary_str = page_repository.get_book_glossary(db, book_id)
    try:
        full_glossary_dict = json.loads(raw_glossary_str)
    except Exception:
        full_glossary_dict = {}

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

        # SENİN SİHRİN BURADA ÇALIŞIYOR
        mini_glossary_dict = filter_glossary_for_text(full_glossary_dict, block.content)
        mini_glossary_json_str = json.dumps(mini_glossary_dict, ensure_ascii=False)

        try:
            translated = gemini_rag_service.translate_block_with_context(
                current_text=block.content,
                prev_text=context.prev_text,
                next_text=context.next_text,
                target_lang=payload.target_lang,
                filtered_glossary_json=mini_glossary_json_str,
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


@router.post("/{book_id}/pages/{page_number}/summarize", response_model=SummarizePageResponse)
def summarize_page(
    book_id: int,
    page_number: int,
    payload: SummarizePageRequest,
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

    full_text = "\n\n".join([block.content for block in blocks if block.content])

    raw_glossary_str = page_repository.get_book_glossary(db, book_id)
    try:
        full_glossary_dict = json.loads(raw_glossary_str)
    except Exception:
        full_glossary_dict = {}

    mini_glossary_dict = filter_glossary_for_text(full_glossary_dict, full_text)
    mini_glossary_json_str = json.dumps(mini_glossary_dict, ensure_ascii=False)

    try:
        summary = gemini_rag_service.summarize_text(
            text_content=full_text,
            target_lang=payload.target_lang,
            filtered_glossary_json=mini_glossary_json_str,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {exc}",
        ) from exc

    return SummarizePageResponse(
        book_id=book_id,
        page_number=page_number,
        target_lang=payload.target_lang,
        summary=summary,
    )


@router.post("/{book_id}/summarize", response_model=SummarizeResponse)
def summarize_book_or_chapter(
    book_id: int,
    payload: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Kitabın tamamını veya belirli bir sayfa aralığını Map-Reduce yöntemiyle özetle.
    
    - Metin ~15.000 karakterlik parçalara bölünür (word boundary korunur)
    - Her parça için ayrı özet çıkarılır (Map faz) - 2 saniye delay
    - Tüm özetler birleştirilerek master özet oluşturulur (Reduce faz)
    
    Query Parametreleri:
    - target_lang: Hedef dil (varsayılan: "tr")
    - start_page: Başlangıç sayfa (isteğe bağlı)
    - end_page: Bitiş sayfa (isteğe bağlı)
    
    NOT: Aynı sayfa aralığı ve dil kombinasyonu için daha önce oluşturulmuş özet varsa,
         Map-Reduce işlemine girmeden doğrudan önbellekten döner.
    """
    book = book_repository.get_book_by_id(db, book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    if book.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # ADIM 1: Önbelleği kontrol et
    cached = page_repository.get_cached_summary(
        db=db,
        book_id=book_id,
        target_lang=payload.target_lang,
        start_page=payload.start_page,
        end_page=payload.end_page,
    )
    
    if cached:
        # Önbellekte varsa, direkt döndür (Map-Reduce'e girmeden)
        return SummarizeResponse(
            book_id=book_id,
            target_lang=payload.target_lang,
            start_page=payload.start_page,
            end_page=payload.end_page,
            summary=cached.summary_text,
        )

    # ADIM 2: Blokları al (sayfa aralığı varsa, yoksa tamamını)
    if payload.start_page and payload.end_page:
        # Sayfa aralığı sorgusu
        blocks = page_repository.get_pages_range(
            db=db,
            book_id=book_id,
            start_page=payload.start_page,
            end_page=payload.end_page,
        )
        if not blocks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No blocks found for pages {payload.start_page}-{payload.end_page}",
            )
        # blocks burada SimpleNamespace döner; content özniteliğini çıkar
        full_text = "\n\n".join([
            (b.content if hasattr(b, 'content') else b.get('content', ''))
            for b in blocks
        ])
    else:
        # Tüm kitabı al
        all_blocks = page_repository.get_book_blocks(db, book_id)
        if not all_blocks:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book has no blocks")
        full_text = "\n\n".join([block.content for block in all_blocks if block.content])

    if not full_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No content found to summarize")

    # ADIM 3: Sözlük bağlamı al
    raw_glossary_str = page_repository.get_book_glossary(db, book_id)
    try:
        full_glossary_dict = json.loads(raw_glossary_str)
    except Exception:
        full_glossary_dict = {}

    mini_glossary_dict = filter_glossary_for_text(full_glossary_dict, full_text)
    mini_glossary_json_str = json.dumps(mini_glossary_dict, ensure_ascii=False)

    # ADIM 4: Metni parçala
    chunks = chunk_text(full_text, max_chars=15000)

    if not chunks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not chunk text")

    # ADIM 5: MAP FAS - Her parçayı özetle
    chunk_summaries = []
    try:
        for i, chunk in enumerate(chunks):
            summary = gemini_rag_service.summarize_chunk(
                text_chunk=chunk,
                target_lang=payload.target_lang,
                filtered_glossary_json=mini_glossary_json_str,
            )
            chunk_summaries.append(summary)
            
            # Rate limiting: her API çağrısından sonra 2 saniye bekle (son chunk'tan sonra bekleme)
            if i < len(chunks) - 1:
                time.sleep(2)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chunk summarization failed: {exc}",
        ) from exc

    # ADIM 6: REDUCE FAS - Tüm özetleri birleştir ve master özet yap
    if len(chunks) == 1:
        # Tek parça varsa, zaten özetlenmiştir
        master_summary = chunk_summaries[0]
    else:
        combined_summaries = "\n\n".join(chunk_summaries)
        try:
            master_summary = gemini_rag_service.summarize_master(
                combined_summaries=combined_summaries,
                target_lang=payload.target_lang,
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Master summarization failed: {exc}",
            ) from exc

    # ADIM 7: Önbelleğe kaydet ve döndür
    page_repository.create_cached_summary(
        db=db,
        book_id=book_id,
        target_lang=payload.target_lang,
        start_page=payload.start_page,
        end_page=payload.end_page,
        summary_text=master_summary,
    )

    return SummarizeResponse(
        book_id=book_id,
        target_lang=payload.target_lang,
        start_page=payload.start_page,
        end_page=payload.end_page,
        summary=master_summary,
    )
