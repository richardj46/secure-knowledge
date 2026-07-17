from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None
    text: str


@dataclass(frozen=True)
class ExtractionResult:
    pages: list[ExtractedPage]

    @property
    def full_text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


class DocumentExtractor(Protocol):
    def extract(self, content: bytes) -> ExtractionResult:
        ...
