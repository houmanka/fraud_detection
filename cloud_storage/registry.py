from enum import Enum
from typing import Callable, Dict

from config import Config
from cloud_storage.contract import CloudStorage


class CloudStorageKind(str, Enum):
    LocalCloud = "local_fs"

_REGISTRY: Dict[CloudStorageKind, Callable[[Config], CloudStorage]] = {}

def register(kind: CloudStorageKind):
    def deco(factory: Callable[[Config], CloudStorage]):
        _REGISTRY[kind] = factory
        return factory
    return deco

def build_cloud_storage(kind: CloudStorageKind, config: Config) -> CloudStorage:
    try:
        return _REGISTRY[kind](config)
    except KeyError:
        raise ValueError(f"Unknown cloud storage kind: {kind}")
