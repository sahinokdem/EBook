"""
PDF Parser Service (Block/Chunk Based)

PDF dosyasını RAG için blok/paragraf tabanlı parse eder.
PyMuPDF page.get_text("blocks") kullanır.

Kurulum:
    pip install PyMuPDF

Özellikler:
- Sayfa bazlı değil blok bazlı extraction
- Anlamsal bütünlük korunarak chunk üretimi
- Karakter limiti kontrollü birleştirme
"""

import fitz  # PyMuPDF
from typing import List, Optional
from dataclasses import dataclass
import re


@dataclass
class ParsedBlock:
    """Parse edilmiş blok/chunk verisi."""
    page_number: int
    block_index: int
    content: str
    word_count: int
    char_count: int


@dataclass
class ParseResult:
    """Parse işlemi sonucu."""
    success: bool
    blocks: List[ParsedBlock]
    total_blocks: int
    error_message: Optional[str] = None

    @property
    def pages(self):
        """Geriye dönük uyumluluk: eski kod result.pages bekliyorsa çalışsın."""
        return self.blocks

    @property
    def total_pages(self):
        """Geriye dönük uyumluluk: eski kod result.total_pages bekliyorsa çalışsın."""
        return self.total_blocks


class PDFParser:
    """
    PDF Parser - PDF'den HTML formatında içerik çıkarır.
    
    Kullanım:
        parser = PDFParser()
        result = parser.parse_file(file_bytes)
        
        for page in result.pages:
            print(f"Sayfa {page.page_number}: {page.word_count} kelime")
            print(page.content)  # HTML içerik
    """
    
    # Chunking thresholds
    MIN_BLOCK_CHARS = 80
    MAX_BLOCK_CHARS = 900
    
    def __init__(self):
        """Parser'ı başlat."""
        pass
    
    def parse_file(self, file_content: bytes) -> ParseResult:
        """
        PDF dosyasını parse et.
        
        Args:
            file_content: PDF dosyası içeriği (bytes)
            
        Returns:
            ParseResult: Parse sonucu (pages, total_pages, error)
        """
        try:
            # PDF'i aç
            doc = fitz.open(stream=file_content, filetype="pdf")
            
            blocks: List[ParsedBlock] = []
            
            for page_num in range(len(doc)):
                # Her sayfadaki blokları parse et
                page = doc[page_num]
                page_blocks = self._parse_page_blocks(page, page_num + 1)
                blocks.extend(page_blocks)
            
            doc.close()
            
            return ParseResult(
                success=True,
                blocks=blocks,
                total_blocks=len(blocks),
                error_message=None
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                blocks=[],
                total_blocks=0,
                error_message=str(e)
            )
    
    def parse_file_from_path(self, file_path: str) -> ParseResult:
        """
        Dosya yolundan PDF parse et.
        
        Args:
            file_path: PDF dosya yolu
            
        Returns:
            ParseResult: Parse sonucu
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return self.parse_file(content)
        except Exception as e:
            return ParseResult(
                success=False,
                blocks=[],
                total_blocks=0,
                error_message=f"Dosya okunamadı: {str(e)}"
            )
    
    def _parse_page_blocks(self, page: fitz.Page, page_number: int) -> List[ParsedBlock]:
        """
        Tek bir sayfadaki text block'ları parse et ve semantic chunk'lara dönüştür.
        
        Args:
            page: PyMuPDF Page objesi
            page_number: Sayfa numarası (1'den başlar)
            
        Returns:
            List[ParsedBlock]: Parse edilmiş bloklar
        """
        raw_blocks = page.get_text("blocks")

        normalized_blocks: List[str] = []
        for block in raw_blocks:
            if len(block) < 5:
                continue
            text = str(block[4]).strip()
            if not text:
                continue
            text = self._normalize_text(text)
            if text:
                normalized_blocks.append(text)

        semantic_chunks = self._build_semantic_chunks(normalized_blocks)

        parsed_blocks: List[ParsedBlock] = []
        for block_index, chunk in enumerate(semantic_chunks):
            parsed_blocks.append(
                ParsedBlock(
                    page_number=page_number,
                    block_index=block_index,
                    content=chunk,
                    word_count=len(chunk.split()),
                    char_count=len(chunk),
                )
            )

        return parsed_blocks

    def _normalize_text(self, text: str) -> str:
        """Block metnini normalize et."""
        text = text.replace("\r", "\n")
        text = re.sub(r"-\n", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _build_semantic_chunks(self, blocks: List[str]) -> List[str]:
        """
        Raw block listesini anlamsal bütünlüğü koruyarak chunk'lara dönüştür.

        Kurallar:
        - Çok kısa bloklar komşu bloklarla birleştirilir.
        - Maksimum karakter sınırı aşılırsa yeni chunk açılır.
        """
        if not blocks:
            return []

        chunks: List[str] = []
        current = ""

        for block in blocks:
            candidate = f"{current}\n\n{block}".strip() if current else block

            if len(candidate) <= self.MAX_BLOCK_CHARS:
                current = candidate
                continue

            if current:
                chunks.append(current.strip())
                current = ""

            # Tek blok çok uzunsa paragraf/satır kırılımlarından böl
            if len(block) > self.MAX_BLOCK_CHARS:
                split_blocks = self._split_long_block(block)
                chunks.extend(split_blocks[:-1])
                current = split_blocks[-1] if split_blocks else ""
            else:
                current = block

            if current and len(current) >= self.MIN_BLOCK_CHARS:
                continue

        if current:
            # Son chunk çok kısaysa bir öncekiyle birleştir
            if chunks and len(current) < self.MIN_BLOCK_CHARS:
                merged = f"{chunks[-1]}\n\n{current}".strip()
                if len(merged) <= self.MAX_BLOCK_CHARS:
                    chunks[-1] = merged
                else:
                    chunks.append(current.strip())
            else:
                chunks.append(current.strip())

        return [chunk for chunk in chunks if chunk]

    def _split_long_block(self, block: str) -> List[str]:
        """Uzun bir bloğu cümle/paragraf düzeyinde güvenli boyutlara böl."""
        paragraphs = [p.strip() for p in re.split(r"\n\n+", block) if p.strip()]
        if not paragraphs:
            return [block[: self.MAX_BLOCK_CHARS].strip()]

        out: List[str] = []
        current = ""

        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(candidate) <= self.MAX_BLOCK_CHARS:
                current = candidate
                continue

            if current:
                out.append(current.strip())

            if len(paragraph) <= self.MAX_BLOCK_CHARS:
                current = paragraph
                continue

            sentence_parts = re.split(r"(?<=[.!?])\s+", paragraph)
            temp = ""
            for sentence in sentence_parts:
                candidate_sentence = f"{temp} {sentence}".strip() if temp else sentence
                if len(candidate_sentence) <= self.MAX_BLOCK_CHARS:
                    temp = candidate_sentence
                else:
                    if temp:
                        out.append(temp.strip())
                    temp = sentence[: self.MAX_BLOCK_CHARS].strip()
            current = temp

        if current:
            out.append(current.strip())

        return out


# Singleton instance
pdf_parser = PDFParser()
