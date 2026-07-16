from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from secure_knowledge_core.ingestion.exceptions import (
    CorruptedDocumentError,
    OcrRequiredError,
    UnsupportedEncryptedDocumentError,
)
from secure_knowledge_core.ingestion.extractors.interface import (
    ExtractedPage,
    ExtractionResult,
)

MINIMUM_EXTRACTED_CHARACTERS = 20


class PdfExtractor:
    def extract(self, content: bytes) -> ExtractionResult:
        try:
            reader = PdfReader(BytesIO(content))
        except PdfReadError:
            raise CorruptedDocumentError from None

        if reader.is_encrypted:
            raise UnsupportedEncryptedDocumentError(
                "Encrypted PDF documents are not supported."
            )

        try:
            pages = [
                ExtractedPage(
                    page_number=index,
                    text=page.extract_text() or "",
                )
                for index, page in enumerate(reader.pages, start=1)
            ]
        except PdfReadError:
            raise CorruptedDocumentError from None
        result = ExtractionResult(pages=pages)
        extracted_character_count = sum(
            not character.isspace() for character in result.full_text
        )

        if extracted_character_count < MINIMUM_EXTRACTED_CHARACTERS:
            raise OcrRequiredError(
                "The PDF contains too little extractable text and requires OCR."
            )

        return result
