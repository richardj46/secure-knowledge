class IngestionError(Exception):
    """Base class for ingestion failures."""

    code = "ingestion_failed"
    public_message = "Document processing failed."


class TransientIngestionError(IngestionError):
    """An ingestion failure that may succeed when retried."""


class PermanentIngestionError(IngestionError):
    """An ingestion failure that will not be fixed by retrying."""

    code = "permanent_ingestion_error"


class UnsupportedEncryptedDocumentError(PermanentIngestionError):
    """The document is encrypted and cannot be extracted."""

    code = "encrypted_pdf"
    public_message = "Encrypted PDF documents are not supported."


class OcrRequiredError(PermanentIngestionError):
    """The PDF does not contain enough extractable text."""

    code = "ocr_required"
    public_message = "The document contains no extractable text and may require OCR."


class UnsupportedTextEncodingError(PermanentIngestionError):
    """The plain-text document is not valid UTF-8."""

    code = "unsupported_text_encoding"
    public_message = "Plain-text documents must use UTF-8 encoding."


class EmbeddingConfigurationError(PermanentIngestionError):
    """The embedding provider is not configured correctly."""

    code = "embedding_not_configured"
    public_message = "The embedding service is not configured."


class EmbeddingProviderError(TransientIngestionError):
    """The embedding provider returned an invalid result."""

    code = "embedding_provider_error"
    public_message = "The embedding service could not process the document."


class StorageDownloadError(TransientIngestionError):
    """The original document could not be downloaded from object storage."""

    code = "storage_download_failed"
    public_message = "The stored document could not be retrieved."


class DocumentVersionNotFoundError(IngestionError):
    """The requested document version does not exist."""


class UnsupportedDocumentTypeError(PermanentIngestionError):
    """No extractor is available for the document MIME type."""

    code = "unsupported_file_type"
    public_message = "The document file type is not supported."


class CorruptedDocumentError(PermanentIngestionError):
    """The uploaded document cannot be parsed."""

    code = "corrupted_document"
    public_message = "The document is corrupted or cannot be read."


class NoExtractableTextError(PermanentIngestionError):
    """The document did not contain enough normalized text."""

    code = "no_extractable_text"
    public_message = "The document contains no extractable text."


class NoChunksGeneratedError(PermanentIngestionError):
    """The document did not produce any non-empty chunks."""

    code = "no_chunks_generated"
    public_message = "The document contains no content that can be indexed."


class EmbeddingCountMismatchError(TransientIngestionError):
    """The provider returned a different number of vectors than inputs."""

    code = "embedding_provider_error"
    public_message = "The embedding service could not process the document."
