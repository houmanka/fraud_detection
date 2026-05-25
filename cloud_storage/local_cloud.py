from pathlib import Path
from typing import Iterator

from cloud_storage.contract import CloudStorage
from cloud_storage.registry import register, CloudStorageKind
from config import Config


class LocalCloudStorage(CloudStorage):
    def __init__(self, config: Config):
        # Config is accepted for factory consistency, even if LocalCloud doesn't need it yet.
        self._config = config

    def iter_text_lines(self, bucket: str, blob_name: str) -> Iterator[str]:
        """Yield UTF-8 lines from a local file path.

        For local development, we treat:
        - `bucket` as a base directory (optional)
        - `blob_name` as a relative path under that directory (or an absolute/relative path if bucket is empty)
        """

        base = Path(bucket) if bucket else Path()
        file_path = (base / blob_name).expanduser()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found at: {file_path}")
        if not file_path.is_file():
            raise FileNotFoundError(f"Not a file: {file_path}")

        def reader() -> Iterator[str]:
            with file_path.open(mode="r", encoding="utf-8") as file:
                for line in file:
                    yield line.rstrip("\n")

        return reader()


@register(CloudStorageKind.LocalCloud)
def create_local_store(config: Config):
    return LocalCloudStorage(config)
