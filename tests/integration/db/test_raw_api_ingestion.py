import pytest
from factories import build_raw_api_ingestion
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from financial_pipeline.db.orm_models import RawApiIngestion

pytestmark = pytest.mark.integration


def test_persists_raw_api_ingestion(
    db_session: Session,
) -> None:
    ingestion = build_raw_api_ingestion()

    db_session.add(ingestion)
    db_session.flush()

    ingestion_id = ingestion.ingestion_id

    db_session.expire_all()

    result = db_session.get(
        RawApiIngestion,
        ingestion_id,
    )

    assert result is not None
    assert result.source_name == "frankfurter"
    assert result.provider == "ECB"
    assert result.payload_hash == "a" * 64
    assert result.request_parameters["base"] == "EUR"
    assert len(result.response_payload) == 1
    assert result.fetched_at is not None


@pytest.mark.parametrize(
    "invalid_payload_hash",
    [
        "abc",
        "g" * 64,
        "A" * 64,
        "a" * 63,
    ],
)
def test_rejects_payload_hash_that_violates_format(
    db_session: Session,
    invalid_payload_hash: str,
) -> None:
    ingestion = build_raw_api_ingestion(
        payload_hash=invalid_payload_hash,
    )

    db_session.add(ingestion)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_rejects_payload_hash_longer_than_column_limit(
    db_session: Session,
) -> None:
    ingestion = build_raw_api_ingestion(
        payload_hash="a" * 65,
    )

    db_session.add(ingestion)

    with pytest.raises(DataError):
        db_session.flush()

    db_session.rollback()
