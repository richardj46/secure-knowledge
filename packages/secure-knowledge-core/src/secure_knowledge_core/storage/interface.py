from typing import BinaryIO, Protocol


class ObjectStorage(Protocol):
    def upload(
        self,
        *,
        file_object: BinaryIO,
        key: str,
        content_type: str,
    ) -> None:
        ...

    def download(self, *, key: str) -> bytes:
        ...

    def delete(self, *, key: str) -> None:
        ...

    def exists(self, *, key: str) -> bool:
        ...