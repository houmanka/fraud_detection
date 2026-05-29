from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class Classification:
    id: int
    name: str

@dataclass
class File:
    id: int
    name: str
    path: str

@dataclass
class FileInput:
    name: str
    path: str

@dataclass
class Complaint:
    case_id: str
    text_redacted: str
    classification: Classification
    file_id: int
    embedded: bool = False
    id: Optional[int] = None





class DataStore(Protocol):
    def save_complaint(self, complaint: Complaint) -> Complaint: ...
    def fetch_complaint(self, complaint_id: int) -> Optional[Complaint]: ...
    def fetch_by_case_id(self, case_id: str) -> Optional[Complaint]: ...
    def fetch_unembedded(self, file_id: int) -> list[Complaint]: ...
    def mark_embedded(self, complaint_id: int) -> None: ...
    def save_classification(self, name: str) -> Classification: ...
    def save_file(self, file_input: FileInput) -> File: ...
    def archive_file(self, file_id: int) -> None: ...
