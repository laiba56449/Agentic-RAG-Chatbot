import os
import uuid
from abc import ABC, abstractmethod


class FileStorage(ABC):
    @abstractmethod
    def save(self, file_bytes: bytes, original_filename: str) -> str:
        """Persist file bytes; return a storage_path/key that can later be used to retrieve or delete it."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def read(self, storage_path: str) -> bytes:
        raise NotImplementedError


class LocalFileStorage(FileStorage):
    def __init__(self, base_dir: str = "uploaded_files"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, file_bytes: bytes, original_filename: str) -> str:
        ext = os.path.splitext(original_filename)[1]
        unique_name = f"{uuid.uuid4()}{ext}"
        full_path = os.path.join(self.base_dir, unique_name)

        with open(full_path, "wb") as f:
            f.write(file_bytes)

        return full_path

    def delete(self, storage_path: str) -> None:
        if os.path.exists(storage_path):
            os.remove(storage_path)

    def read(self, storage_path: str) -> bytes:
        with open(storage_path, "rb") as f:
            return f.read()


def get_storage() -> FileStorage:
    return LocalFileStorage()