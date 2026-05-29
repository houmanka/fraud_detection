from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, Text, String, DateTime, Boolean, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import relationship

from config import Config
from storage.contract import DataStore, Complaint, Classification, FileInput, File

Base = declarative_base()

def get_utc_now():
    """Helper to ensure we always use timezone-aware UTC."""
    return datetime.now(timezone.utc)

class _Complaints(Base):
    __tablename__ = 'complaints'

    id = Column(Integer, primary_key=True)
    case_id = Column(String(64), nullable=False, index=True, unique=True)

    text_redacted = Column(Text, nullable=False)
    embedded = Column(Boolean, default=False, nullable=False)
    file_id = Column(Integer, ForeignKey('files.id'), nullable=False)
    classification_id = Column(Integer, ForeignKey('classifications.id'), nullable=False)
    classification_rel = relationship("_Classifications", lazy="joined")
    # Timestamps
    # Note: We pass the function itself (get_utc_now) to 'default'
    # so it executes at the moment of insertion.
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    updated_at = Column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    embedded_at = Column(DateTime(timezone=True), nullable=True)

class _Files(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    file_name = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    path = Column(String(256), nullable=False)

class _Classifications(Base):
    __tablename__ = 'classifications'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, index=True, unique=True)

class _PostgresStore(DataStore):
    def __init__(self, config: Config) -> None:
        self.config = config
        self.engine = create_engine(self.config.database_url.get_secret_value(), future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def save_complaint(self, complaint: Complaint) -> Complaint:
        insert = pg_insert(_Complaints).values(
            case_id=complaint.case_id,
            text_redacted=complaint.text_redacted,
            file_id=complaint.file_id,
            classification_id=complaint.classification.id,
        )
        update = insert.on_conflict_do_nothing()
        with self.SessionLocal() as session:
            session.execute(update)
            session.commit()
            saved = session.query(_Complaints).filter(_Complaints.case_id == complaint.case_id).first()
            if not saved:
                raise ValueError(f"failed to save complaint: {complaint.case_id}")
            return Complaint(
                id=saved.id,
                case_id=saved.case_id,
                text_redacted=saved.text_redacted,
                file_id=saved.file_id,
                embedded=saved.embedded,
                classification=Classification(id=saved.classification_rel.id, name=saved.classification_rel.name),
            )

    def fetch_complaint(self, complaint_id: int) -> Optional[Complaint]:
        with self.SessionLocal() as session:
            complaint = session.query(_Complaints).filter(_Complaints.id == complaint_id).first()
            if not complaint:
                return None
            return Complaint(
                id=complaint.id,
                case_id=complaint.case_id,
                text_redacted=complaint.text_redacted,
                embedded=complaint.embedded,
                file_id=complaint.file_id,
                classification=Classification(id=complaint.classification_rel.id, name=complaint.classification_rel.name),
            )

    def fetch_by_case_id(self, case_id: str) -> Optional[Complaint]: ...
    def fetch_by_classification(self, classification_id: int) -> Complaint: ...
    def fetch_unembedded(self, file_id: int) -> list[Complaint]: ...
    def mark_embedded(self, complaint_id: int) -> None: ...

    def save_classification(self, name: str) -> Classification:
        insert = pg_insert(_Classifications).values(name=name)
        update = insert.on_conflict_do_nothing()
        with self.SessionLocal() as session:
            session.execute(update)
            session.commit()
            saved = session.query(_Classifications).filter(_Classifications.name == name).first()
            if not saved:
                raise ValueError(f"failed to save classification: {name}")
            return Classification(id=saved.id, name=saved.name)

    def save_file(self, file_input: FileInput) -> File:
        insert = pg_insert(_Files).values(file_name=file_input.name, path=file_input.path)
        update_stmt = insert.on_conflict_do_nothing()
        with self.SessionLocal() as session:
            session.execute(update_stmt)
            session.commit()
            saved = session.query(_Files).filter(_Files.file_name == file_input.name).first()
            if not saved:
                raise ValueError(f"failed to save file: {file_input.name}")
            return File(id=saved.id, name=saved.file_name, path=saved.path)


    def archive_file(self, file_id: int) -> None: ...