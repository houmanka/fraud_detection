from typing import Protocol, Iterator


class CloudStorage(Protocol):
    def iter_text_lines(self, bucket: str, blob_name: str) -> Iterator[str]: ...