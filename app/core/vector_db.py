from __future__ import annotations

from typing import List, Dict, Any
import uuid
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PayloadSchemaType
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

from app.core.config import settings


class VectorDBService:
    def __init__(self) -> None:
        self._embedder = None
        self._vector_size = None
        self._client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
            timeout=30,
        )

    def _ensure_embedder(self) -> None:
        if self._embedder is None:
            self._embedder = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            self._vector_size = self._embedder.get_sentence_embedding_dimension()

    @property
    def collection_name(self) -> str:
        return settings.QDRANT_COLLECTION_NAME

    def _ensure_collection(self) -> None:
        self._ensure_embedder()
        existing = [collection.name for collection in self._client.get_collections().collections]
        if self.collection_name not in existing:
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )
            # --- YENİ EKLENEN INDEX KISMI ---
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=PayloadSchemaType.INTEGER,
            )
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="book_id",
                field_schema=PayloadSchemaType.INTEGER,
            )
            # --------------------------------

    def embed_text(self, text: str) -> List[float]:
        self._ensure_embedder()
        return self._embedder.encode(text, normalize_embeddings=True).tolist()

    def index_block(
        self,
        *,
        block_id: str,
        book_id: int,
        user_id: int,
        page_number: int,
        block_index: int,
        content: str,
    ) -> str:
        vector = self.embed_text(content)
        self._ensure_collection()
        payload = {
            "book_id": book_id,
            "user_id": user_id,
            "page_number": page_number,
            "block_index": block_index,
            "content": content,
        }
        self._client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=block_id, vector=vector, payload=payload)],
        )
        return block_id

    def index_blocks(self, *, book_id: int, user_id: int, blocks: List[Dict[str, Any]]) -> List[str]:
        points: List[PointStruct] = []
        ids: List[str] = []

        self._ensure_collection()

        for block in blocks:
            block_id = block.get("vector_id") or str(uuid.uuid4())
            vector = self.embed_text(block["content"])
            points.append(
                PointStruct(
                    id=block_id,
                    vector=vector,
                    payload={
                        "book_id": book_id,
                        "user_id": user_id,
                        "page_number": block["page_number"],
                        "block_index": block.get("block_index", 0),
                        "content": block["content"],
                    },
                )
            )
            ids.append(block_id)

        if points:
            self._client.upsert(collection_name=self.collection_name, points=points)

        return ids

    def search_similar_blocks(
        self,
        *,
        query: str,
        user_id: int,
        book_id: int,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        query_vector = self.embed_text(query)
        self._ensure_collection()
        query_filter = Filter(
            must=[
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="book_id", match=MatchValue(value=book_id)),
            ]
        )

        response = self._client.query_points(
            collection_name=self.collection_name,
            query=query_vector,  # query_vector yerine sadece query yazıyoruz
            query_filter=query_filter,
            limit=limit,
        )

        mapped: List[Dict[str, Any]] = []
        for item in response.points:  # response.points içinde dönüyoruz
            payload = item.payload or {}
            mapped.append(
                {
                    "vector_id": str(item.id),
                    "score": float(item.score),
                    "book_id": payload.get("book_id"),
                    "user_id": payload.get("user_id"),
                    "page_number": payload.get("page_number"),
                    "block_index": payload.get("block_index"),
                    "content": payload.get("content", ""),
                }
            )
        return mapped


class GeminiRAGService:
    def __init__(self) -> None:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(settings.GEMINI_MODEL)
        else:
            self._model = None

    def answer(self, *, question: str, context_blocks: List[Dict[str, Any]]) -> str:
        if self._model is None:
            raise RuntimeError("Gemini API key is not configured")

        context_text = "\n\n".join(
            [
                f"[Page {block.get('page_number')} Block {block.get('block_index')}]\n{block.get('content', '')}"
                for block in context_blocks
            ]
        )

        prompt = (
            "You are an assistant answering questions from an eBook. "
            "Use only the context below. If context is insufficient, explicitly say so.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        response = self._model.generate_content(
            prompt,
            generation_config={
                "temperature": settings.GEMINI_TEMPERATURE,
                "max_output_tokens": settings.GEMINI_MAX_TOKENS,
            },
        )
        return (response.text or "").strip()


vector_db_service = VectorDBService()
gemini_rag_service = GeminiRAGService()
