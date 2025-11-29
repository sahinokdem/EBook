"""
PDF Parser Service

PDF dosyasını parse edip HTML formatında içerik çıkarır.
PyMuPDF (fitz) kullanır - en iyi formatting desteği sağlar.

Kurulum:
    pip install PyMuPDF

Özellikler:
- Başlık tespiti (font size'a göre)
- Paragraf ayrımı
- Bold/Italic tespit
- Satır birleştirme (hyphenation fix)
"""

import fitz  # PyMuPDF
from typing import List, Dict, Optional, BinaryIO
from dataclasses import dataclass
from pathlib import Path
import re
import html


@dataclass
class ParsedPage:
    """Parse edilmiş sayfa verisi."""
    page_number: int
    content: str  # HTML formatted
    word_count: int
    char_count: int


@dataclass
class ParseResult:
    """Parse işlemi sonucu."""
    success: bool
    pages: List[ParsedPage]
    total_pages: int
    error_message: Optional[str] = None


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
    
    # Font size thresholds (başlık tespiti için)
    H1_MIN_SIZE = 18  # 18pt ve üstü → <h1>
    H2_MIN_SIZE = 14  # 14-17pt → <h2>
    H3_MIN_SIZE = 12  # 12-13pt → <h3>
    
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
            
            pages: List[ParsedPage] = []
            
            for page_num in range(len(doc)):
                # Her sayfayı parse et
                page = doc[page_num]
                parsed_page = self._parse_page(page, page_num + 1)
                pages.append(parsed_page)
            
            doc.close()
            
            return ParseResult(
                success=True,
                pages=pages,
                total_pages=len(pages),
                error_message=None
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                pages=[],
                total_pages=0,
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
                pages=[],
                total_pages=0,
                error_message=f"Dosya okunamadı: {str(e)}"
            )
    
    def _parse_page(self, page: fitz.Page, page_number: int) -> ParsedPage:
        """
        Tek bir sayfayı parse et.
        
        Args:
            page: PyMuPDF Page objesi
            page_number: Sayfa numarası (1'den başlar)
            
        Returns:
            ParsedPage: Parse edilmiş sayfa
        """
        # Text blocks'ları al (formatting bilgisiyle)
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        
        html_parts: List[str] = []
        plain_text_parts: List[str] = []
        
        for block in blocks:
            # Sadece text block'ları işle (image block'ları atla)
            if block.get("type") != 0:  # 0 = text, 1 = image
                continue
            
            block_html = self._process_block(block)
            if block_html:
                html_parts.append(block_html)
                # Plain text (word count için)
                plain_text = self._strip_html(block_html)
                plain_text_parts.append(plain_text)
        
        # HTML içeriği birleştir
        content = "\n".join(html_parts)
        
        # Temizlik
        content = self._clean_html(content)
        
        # Plain text (metrics için)
        plain_text = " ".join(plain_text_parts)
        word_count = len(plain_text.split())
        char_count = len(plain_text)
        
        return ParsedPage(
            page_number=page_number,
            content=content,
            word_count=word_count,
            char_count=char_count
        )
    
    def _process_block(self, block: dict) -> Optional[str]:
        """
        Text block'u HTML'e çevir.
        
        Block yapısı:
        {
            "lines": [
                {
                    "spans": [
                        {"text": "Hello", "size": 12, "flags": 0, "font": "Arial"}
                    ]
                }
            ]
        }
        """
        lines = block.get("lines", [])
        if not lines:
            return None
        
        # Block'taki dominant font size'ı bul (başlık mı?)
        all_spans = []
        for line in lines:
            all_spans.extend(line.get("spans", []))
        
        if not all_spans:
            return None
        
        # Ortalama font size
        avg_size = sum(s.get("size", 12) for s in all_spans) / len(all_spans)
        
        # Tag belirle
        tag = self._get_tag_for_size(avg_size)
        
        # Lines'ları işle
        line_texts: List[str] = []
        
        for line in lines:
            line_html = self._process_line(line)
            if line_html:
                line_texts.append(line_html)
        
        if not line_texts:
            return None
        
        # Satırları birleştir
        text = " ".join(line_texts)
        
        # Hyphenation fix (satır sonundaki - işaretleri)
        text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)
        
        # Tag ile wrap et
        return f"<{tag}>{text}</{tag}>"
    
    def _process_line(self, line: dict) -> Optional[str]:
        """
        Tek satırı HTML'e çevir.
        Span'lardaki formatting'i korur (bold, italic).
        """
        spans = line.get("spans", [])
        if not spans:
            return None
        
        parts: List[str] = []
        
        for span in spans:
            text = span.get("text", "")
            if not text or text.isspace():
                parts.append(" ")
                continue
            
            # HTML escape
            text = html.escape(text)
            
            # Font flags
            flags = span.get("flags", 0)
            
            # Bold check (flags bit 4)
            is_bold = bool(flags & 2 ** 4)
            
            # Italic check (flags bit 1)
            is_italic = bool(flags & 2 ** 1)
            
            # Formatting uygula
            if is_bold and is_italic:
                text = f"<strong><em>{text}</em></strong>"
            elif is_bold:
                text = f"<strong>{text}</strong>"
            elif is_italic:
                text = f"<em>{text}</em>"
            
            parts.append(text)
        
        return "".join(parts)
    
    def _get_tag_for_size(self, font_size: float) -> str:
        """
        Font size'a göre HTML tag belirle.
        
        Args:
            font_size: Font boyutu (pt)
            
        Returns:
            str: HTML tag (h1, h2, h3, p)
        """
        if font_size >= self.H1_MIN_SIZE:
            return "h1"
        elif font_size >= self.H2_MIN_SIZE:
            return "h2"
        elif font_size >= self.H3_MIN_SIZE:
            return "h3"
        else:
            return "p"
    
    def _clean_html(self, html_content: str) -> str:
        """
        HTML içeriği temizle ve düzenle.
        
        - Fazla boşlukları kaldır
        - Boş tag'leri kaldır
        - Art arda gelen aynı tag'leri birleştir
        """
        # Fazla whitespace temizliği
        html_content = re.sub(r'\s+', ' ', html_content)
        
        # Boş paragrafları kaldır
        html_content = re.sub(r'<p>\s*</p>', '', html_content)
        html_content = re.sub(r'<h[1-3]>\s*</h[1-3]>', '', html_content)
        
        # Tag'ler arasındaki boşlukları düzenle
        html_content = re.sub(r'>\s+<', '>\n<', html_content)
        
        return html_content.strip()
    
    def _strip_html(self, html_content: str) -> str:
        """HTML tag'lerini kaldır, plain text döndür."""
        clean = re.sub(r'<[^>]+>', ' ', html_content)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()


# Singleton instance
pdf_parser = PDFParser()
