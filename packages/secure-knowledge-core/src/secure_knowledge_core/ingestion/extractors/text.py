from secure_knowledge_core.ingestion.exceptions import UnsupportedTextEncodingError
from secure_knowledge_core.ingestion.extractors.interface import (
    ExtractedPage,
    ExtractionResult,
)


class PlainTextExtractor:
    def extract(self, content: bytes) -> ExtractionResult:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            raise UnsupportedTextEncodingError(
                "Plain-text documents must use UTF-8 encoding."
            ) from None

        return ExtractionResult(
            pages=[
                ExtractedPage(
                    page_number=None,
                    text=text,
                )
            ]
        )
