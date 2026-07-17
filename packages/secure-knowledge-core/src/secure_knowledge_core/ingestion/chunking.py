import re
from dataclasses import dataclass
from typing import Any

import tiktoken
from pydantic import BaseModel, model_validator

from secure_knowledge_core.ingestion.extractors.interface import ExtractionResult
from secure_knowledge_core.ingestion.normalization import normalize_text


class ChunkingSettings(BaseModel):
    target_tokens: int = 500
    overlap_tokens: int = 75
    maximum_tokens: int = 700

    @model_validator(mode="after")
    def validate_token_limits(self) -> "ChunkingSettings":
        if self.target_tokens <= 0:
            raise ValueError("target_tokens must be greater than zero.")
        if self.overlap_tokens < 0:
            raise ValueError("overlap_tokens cannot be negative.")
        if self.overlap_tokens >= self.target_tokens:
            raise ValueError("overlap_tokens must be smaller than target_tokens.")
        if self.maximum_tokens < self.target_tokens:
            raise ValueError("maximum_tokens cannot be smaller than target_tokens.")
        return self


@dataclass(frozen=True)
class ChunkDraft:
    chunk_index: int
    content: str
    token_count: int
    page_number: int | None
    section_title: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class _TextFragment:
    content: str
    page_number: int | None


class ParagraphTokenChunker:
    def __init__(
        self,
        *,
        settings: ChunkingSettings | None = None,
        encoding_name: str = "cl100k_base",
    ) -> None:
        self.settings = settings or ChunkingSettings()
        self.encoding = tiktoken.get_encoding(encoding_name)

    def chunk(self, extraction: ExtractionResult) -> list[ChunkDraft]:
        fragments = self._build_fragments(extraction)
        chunks: list[ChunkDraft] = []
        current: list[_TextFragment] = []

        for fragment in fragments:
            if not current:
                current = [fragment]
                continue

            candidate = [*current, fragment]
            if self._token_count(candidate) <= self.settings.target_tokens:
                current = candidate
                continue

            chunks.append(self._build_chunk(len(chunks), current))
            overlap = self._build_overlap(current)
            candidate = [*overlap, fragment]

            if self._token_count(candidate) > self.settings.maximum_tokens:
                candidate = [fragment]

            current = candidate

        if current:
            chunks.append(self._build_chunk(len(chunks), current))

        return chunks

    def _build_fragments(self, extraction: ExtractionResult) -> list[_TextFragment]:
        fragments: list[_TextFragment] = []

        for page in extraction.pages:
            normalized_page = normalize_text(page.text)
            if not normalized_page:
                continue

            paragraphs = re.split(r"\n\s*\n", normalized_page)
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue

                token_ids = self.encoding.encode(paragraph)
                if len(token_ids) <= self.settings.target_tokens:
                    fragments.append(
                        _TextFragment(
                            content=paragraph,
                            page_number=page.page_number,
                        )
                    )
                    continue

                for start in range(0, len(token_ids), self.settings.target_tokens):
                    content = self.encoding.decode(
                        token_ids[start : start + self.settings.target_tokens]
                    ).strip()
                    if content:
                        fragments.append(
                            _TextFragment(
                                content=content,
                                page_number=page.page_number,
                            )
                        )

        return fragments

    def _build_overlap(
        self,
        fragments: list[_TextFragment],
    ) -> list[_TextFragment]:
        remaining_tokens = self.settings.overlap_tokens
        overlap: list[_TextFragment] = []

        for fragment in reversed(fragments):
            if remaining_tokens <= 0:
                break

            token_ids = self.encoding.encode(fragment.content)
            selected_ids = token_ids[-remaining_tokens:]
            selected_content = self.encoding.decode(selected_ids).strip()

            if selected_content:
                overlap.append(
                    _TextFragment(
                        content=selected_content,
                        page_number=fragment.page_number,
                    )
                )
            remaining_tokens -= len(selected_ids)

        overlap.reverse()
        return overlap

    def _build_chunk(
        self,
        chunk_index: int,
        fragments: list[_TextFragment],
    ) -> ChunkDraft:
        content = self._join_fragments(fragments)
        page_numbers = sorted(
            {
                fragment.page_number
                for fragment in fragments
                if fragment.page_number is not None
            }
        )
        page_number = page_numbers[0] if len(page_numbers) == 1 else None
        metadata: dict[str, Any] = {}

        if len(page_numbers) > 1:
            metadata["page_start"] = page_numbers[0]
            metadata["page_end"] = page_numbers[-1]

        return ChunkDraft(
            chunk_index=chunk_index,
            content=content,
            token_count=len(self.encoding.encode(content)),
            page_number=page_number,
            section_title=None,
            metadata=metadata,
        )

    def _token_count(self, fragments: list[_TextFragment]) -> int:
        return len(self.encoding.encode(self._join_fragments(fragments)))

    @staticmethod
    def _join_fragments(fragments: list[_TextFragment]) -> str:
        return "\n\n".join(fragment.content for fragment in fragments).strip()
