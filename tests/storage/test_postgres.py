import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from config import Config
from storage.contract import Classification
from storage.postgres import Base, _Classifications, _Complaints, _Files, _PostgresStore


@pytest.fixture(scope="module")
def store():
    with PostgresContainer("postgres:16") as pg:
        cfg = Config(database_url=SecretStr(pg.get_connection_url()))
        s = _PostgresStore(cfg)
        Base.metadata.create_all(s.engine)
        yield s


def test_fetch_complaint_returns_complaint_with_classification(store):
    with Session(store.engine) as session:
        cls = _Classifications(name="billing")
        session.add(cls)
        session.flush()

        file = _Files(file_name="test.csv", path="data/inbox/test.csv")
        session.add(file)
        session.flush()

        row = _Complaints(
            case_id="CASE-001",
            text_redacted="My bill is wrong",
            classification_id=cls.id,
            file_id=file.id,
        )
        session.add(row)
        session.commit()
        complaint_id = row.id

    result = store.fetch_complaint(complaint_id)

    assert result is not None
    assert result.id == complaint_id
    assert result.case_id == "CASE-001"
    assert result.text_redacted == "My bill is wrong"
    assert result.embedded is False
    assert isinstance(result.classification, Classification)
    assert result.classification.name == "billing"
