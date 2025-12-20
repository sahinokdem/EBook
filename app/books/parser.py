"""
Unified Book Parser

PDF ve EPUB dosyalarını parse etmek için factory pattern.
File type'a göre uygun parser'ı seçer.
"""

from typing import Union
from app.books.pdf_parser import pdf_parser, ParseResult
from app.books.epub_parser import epub_parser


class BookParser:
    """
    Unified book parser.
    
    File type'ına göre PDF veya EPUB parser kullanır.
    
    Kullanım:
        parser = BookParser()
        result = parser.parse(file_content, file_type)
    """
    
    # Desteklenen MIME types
    PDF_TYPES = {
        "application/pdf",
        "application/x-pdf"
    }
    
    EPUB_TYPES = {
        "application/epub+zip",
        "application/epub"
    }
    
    @classmethod
    def parse(cls, file_content: bytes, file_type: str) -> ParseResult:
        """
        File'ı parse et (type'a göre).
        
        Args:
            file_content: File içeriği (bytes)
            file_type: MIME type (application/pdf, application/epub+zip)
            
        Returns:
            ParseResult: Parse sonucu
            
        Raises:
            ValueError: Desteklenmeyen file type
        """
        # File type normalize
        file_type = file_type.lower().strip()
        
        if file_type in cls.PDF_TYPES:
            return pdf_parser.parse_file(file_content)
        
        elif file_type in cls.EPUB_TYPES:
            return epub_parser.parse_file(file_content)
        
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    
    @classmethod
    def is_supported(cls, file_type: str) -> bool:
        """
        File type destekleniyor mu kontrol et.
        
        Args:
            file_type: MIME type
            
        Returns:
            bool: Destekleniyorsa True
        """
        file_type = file_type.lower().strip()
        return file_type in cls.PDF_TYPES or file_type in cls.EPUB_TYPES
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Desteklenen tüm MIME type'ları döndür.
        
        Returns:
            list[str]: MIME type listesi
        """
        return list(cls.PDF_TYPES | cls.EPUB_TYPES)


# Singleton instance (opsiyonel kullanım için)
book_parser = BookParser()
