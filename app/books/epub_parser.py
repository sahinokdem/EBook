"""
EPUB Parser Service (Block/Chunk Based)

EPUB dosyasını parse edip RAG ve Çeviri için blok/paragraf tabanlı metin çıkarır.
ebooklib kullanır - EPUB 2 ve EPUB 3 desteği.
"""

from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Optional
from dataclasses import dataclass
import re
import tempfile
import os


@dataclass
class ParsedBlock:
    """Parse edilmiş blok/chunk verisi."""
    page_number: int  # EPUB için chapter/item index
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
        return self.blocks

    @property
    def total_pages(self):
        return self.total_blocks


class EPUBParser:
    
    MIN_BLOCK_CHARS = 80
    MAX_BLOCK_CHARS = 900
    
    def parse_file(self, file_content: bytes) -> ParseResult:
        temp_file = None
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.epub')
            temp_file.write(file_content)
            temp_file.close()
            
            book = epub.read_epub(temp_file.name)
            blocks: List[ParsedBlock] = []
            
            # EPUB items'ları al (sadece document items)
            items = list(book.get_items_of_type(9))  # 9 = ITEM_DOCUMENT
            
            for chapter_index, item in enumerate(items, start=1):
                chapter_blocks = self._parse_item_blocks(item, chapter_index)
                blocks.extend(chapter_blocks)
            
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
        finally:
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

    def _parse_item_blocks(self, item, chapter_number: int) -> List[ParsedBlock]:
        """Bölüm HTML'ini okuyup anlamsal chunk'lara böler."""
        content = item.get_content()
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
            
        soup = BeautifulSoup(content, 'lxml')
        
        # Sadece anlamlı metin içeren etiketleri seç
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div'])
        raw_blocks = [elem.get_text(separator=' ', strip=True) for elem in text_elements if elem.get_text(strip=True)]
        
        # Eğer etiket yapısı bozuksa tüm metni al
        if not raw_blocks:
            full_text = soup.get_text(separator=' ', strip=True)
            raw_blocks = [full_text] if full_text else []
            
        semantic_chunks = self._build_semantic_chunks(raw_blocks)
        
        parsed_blocks = []
        for block_index, chunk in enumerate(semantic_chunks):
            parsed_blocks.append(
                ParsedBlock(
                    page_number=chapter_number,
                    block_index=block_index,
                    content=chunk,
                    word_count=len(chunk.split()),
                    char_count=len(chunk)
                )
            )
        return parsed_blocks

    def _build_semantic_chunks(self, blocks: List[str]) -> List[str]:
        """Raw block listesini anlamsal bütünlüğü koruyarak chunk'lara dönüştür."""
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

            if len(block) > self.MAX_BLOCK_CHARS:
                split_blocks = self._split_long_block(block)
                chunks.extend(split_blocks[:-1])
                current = split_blocks[-1] if split_blocks else ""
            else:
                current = block

        if current:
            chunks.append(current.strip())

        return chunks

    def _split_long_block(self, block: str) -> List[str]:
        """Uzun bir bloğu cümle düzeyinde böler."""
        sentences = re.split(r"(?<=[.!?])\s+", block)
        out, temp = [], ""
        for sentence in sentences:
            candidate = f"{temp} {sentence}".strip() if temp else sentence
            if len(candidate) <= self.MAX_BLOCK_CHARS:
                temp = candidate
            else:
                if temp:
                    out.append(temp.strip())
                temp = sentence[:self.MAX_BLOCK_CHARS].strip()
        if temp:
            out.append(temp.strip())
        return out

epub_parser = EPUBParser()