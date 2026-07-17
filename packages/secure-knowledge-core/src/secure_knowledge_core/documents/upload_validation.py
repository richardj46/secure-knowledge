import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol


class UploadValidationError(Exception):
    pass


@dataclass(frozen=True)
class ValidatedUpload:
    filename: str
    content_type: str


@dataclass(frozen=True)
class BufferedUpload:
    file_object: BinaryIO
    checksum: str
    size_bytes: int


class AsyncUploadReader(Protocol):
    filename: str | None
    content_type: str | None

    async def read(self, size: int = -1) -> bytes:
        ...


_ALLOWED_TYPES = {
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
}


def validate_upload_metadata(
    *,
    filename: str | None,
    content_type: str | None,
) -> ValidatedUpload:
    if not filename:
        raise UploadValidationError("Filename is required.")

    normalized_content_type = (content_type or "").lower()
    suffix = Path(filename).suffix.lower()

    allowed_suffixes = _ALLOWED_TYPES.get(normalized_content_type)

    if allowed_suffixes is None or suffix not in allowed_suffixes:
        raise UploadValidationError(
            "Only PDF and plain-text documents are supported."
        )

    return ValidatedUpload(
        filename=Path(filename).name,
        content_type=normalized_content_type,
    )


def validate_file_signature(
    *,
    file_object: BinaryIO,
    content_type: str,
) -> None:
    file_object.seek(0)
    sample = file_object.read(8192)
    file_object.seek(0)

    if not sample:
        raise UploadValidationError("File is empty.")

    if content_type == "application/pdf":
        if not sample.startswith(b"%PDF-"):
            raise UploadValidationError("File content does not match its PDF type.")
        return

    if content_type == "text/plain":
        if b"\x00" in sample:
            raise UploadValidationError("File content is not valid plain text.")

        try:
            sample.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UploadValidationError(
                "Plain-text files must use UTF-8 encoding."
            ) from exc
        return

    raise UploadValidationError("Unsupported content type.")


async def buffer_upload(
    upload_file: AsyncUploadReader,
    *,
    maximum_size: int,
) -> BufferedUpload:
    digest = hashlib.sha256()
    size = 0
    temporary_file = tempfile.SpooledTemporaryFile(
        max_size=5 * 1024 * 1024,
        mode="w+b",
    )

    try:
        while chunk := await upload_file.read(1024 * 1024):
            size += len(chunk)

            if size > maximum_size:
                raise UploadValidationError("File is too large.")

            digest.update(chunk)
            temporary_file.write(chunk)
    except BaseException:
        temporary_file.close()
        raise

    temporary_file.seek(0)

    return BufferedUpload(
        file_object=temporary_file,
        checksum=digest.hexdigest(),
        size_bytes=size,
    )
