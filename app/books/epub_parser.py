"""
EPUB Parser Service

EPUB dosyasını parse edip HTML formatında içerik çıkarır.
ebooklib kullanır - EPUB 2 ve EPUB 3 desteği.

Kurulum:
    pip install ebooklib beautifulsoup4 lxml

Özellikler:
- EPUB 2 ve EPUB 3 desteği
- HTML içeriği çıkarma
- Sayfa/chapter yapısı koruma
- Metadata okuma

NOT: ebooklib.read_epub() sadece dosya yolu kabul eder, bytes kabul etmez.
Bu yüzden bytes verildiğinde geçici dosya oluşturulur.
"""

from ebooklib import epub
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
import re
import html as html_lib
import tempfile
import os


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


class EPUBParser:
    """
    EPUB Parser - EPUB'dan HTML formatında içerik çıkarır.
    
    Kullanım:
        parser = EPUBParser()
        result = parser.parse_file(file_bytes)
        
        for page in result.pages:
            print(f"Sayfa {page.page_number}: {page.word_count} kelime")
            print(page.content)  # HTML içerik
    """
    
    def __init__(self):
        """Parser'ı başlat."""
        pass
    
    def parse_file(self, file_content: bytes) -> ParseResult:
        """
        EPUB dosyasını parse et.
        
        Args:
            file_content: EPUB dosyası içeriği (bytes)
            
        Returns:
            ParseResult: Parse sonucu (pages, total_pages, error)
        """
        # ebooklib.read_epub() sadece file path kabul ediyor, bytes kabul etmiyor!
        # Bu yüzden geçici dosya oluşturuyoruz
        temp_file = None
        try:
            # Geçici dosya oluştur
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.epub')
            temp_file.write(file_content)
            temp_file.close()
            
            # EPUB'u aç (dosya yolundan)
            book = epub.read_epub(temp_file.name)
            
            pages: List[ParsedPage] = []
            page_number = 1
            
            # EPUB items'ları al (sadece document items)
            items = list(book.get_items_of_type(9))  # 9 = ITEM_DOCUMENT
            
            for item in items:
                # Her chapter/section'ı bir sayfa olarak işle
                parsed_page = self._parse_item(item, page_number)
                
                # Boş sayfaları atla
                if parsed_page and parsed_page.word_count > 0:
                    pages.append(parsed_page)
                    page_number += 1
            
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
        finally:
            # Geçici dosyayı temizle
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
    
    def parse_file_from_path(self, file_path: str) -> ParseResult:
        """
        Dosya yolundan EPUB parse et.
        
        Args:
            file_path: EPUB dosya yolu
            
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
    
    def _parse_item(self, item, page_number: int) -> Optional[ParsedPage]:
        """
        Tek bir EPUB item'ı (chapter/section) parse et.
        
        Args:
            item: EpubHtml objesi
            page_number: Sayfa numarası (1'den başlar)
            
        Returns:
            ParsedPage: Parse edilmiş sayfa veya None
        """
        try:
            # HTML içeriğini al
            content = item.get_content()
            
            # Bytes'dan string'e
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # HTML'i temizle ve düzenle
            cleaned_html = self._clean_html(content)
            
            if not cleaned_html:
                return None
            
            # Plain text çıkar (metrics için)
            plain_text = self._html_to_text(cleaned_html)
            
            if not plain_text.strip():
                return None
            
            word_count = len(plain_text.split())
            char_count = len(plain_text)
            
            return ParsedPage(
                page_number=page_number,
                content=cleaned_html,
                word_count=word_count,
                char_count=char_count
            )
            
        except Exception as e:
            # Item parse hatası - skip
            return None
    
    def _clean_html(self, html_content: str) -> str:
        """
        HTML içeriğini temizle ve düzenle.
        
        - Gereksiz tag'leri kaldır (script, style)
        - Inline style'ları kaldır
        - Boş tag'leri kaldır
        - Sadece içerik tag'lerini koru (h1-h6, p, strong, em, ul, ol, li)
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Script ve style tag'lerini kaldır
            for tag in soup(['script', 'style', 'meta', 'link', 'head']):
                tag.decompose()
            
            # Body içeriğini al (varsa)
            body = soup.find('body')
            if body:
                soup = body
            
            # İzin verilen tag'ler
            allowed_tags = {
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                'p', 'br',
                'strong', 'b', 'em', 'i', 'u',
                'ul', 'ol', 'li',
                'blockquote', 'pre', 'code',
                'a', 'img'
            }
            
            # Tag temizliği
            for tag in soup.find_all(True):
                # İzin verilmeyen tag'leri unwrap et (içeriği koru)
                if tag.name not in allowed_tags:
                    tag.unwrap()
                else:
                    # Attribute'ları temizle (href ve src hariç)
                    attrs = dict(tag.attrs)
                    for attr in attrs:
                        if attr not in ['href', 'src', 'alt']:
                            del tag.attrs[attr]
            
            # b → strong, i → em dönüşümü
            for b in soup.find_all('b'):
                b.name = 'strong'
            for i in soup.find_all('i'):
                i.name = 'em'
            
            # HTML string'e çevir
            html_str = str(soup)
            
            # Fazla whitespace temizliği
            html_str = re.sub(r'\s+', ' ', html_str)
            
            # Boş tag'leri kaldır
            html_str = re.sub(r'<(\w+)>\s*</\1>', '', html_str)
            
            # Tag'ler arasındaki boşlukları düzenle
            html_str = re.sub(r'>\s+<', '>\n<', html_str)
            
            return html_str.strip()
            
        except Exception as e:
            # Parsing hatası - orijinal içeriği döndür
            return html_content
    
    def _html_to_text(self, html_content: str) -> str:
        """
        HTML'den plain text çıkar.
        
        Args:
            html_content: HTML string
            
        Returns:
            str: Plain text
        """
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            text = soup.get_text(separator=' ', strip=True)
            # Fazla boşlukları temizle
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except:
            # Fallback: regex ile tag'leri kaldır
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()


# Singleton instance
epub_parser = EPUBParser()
