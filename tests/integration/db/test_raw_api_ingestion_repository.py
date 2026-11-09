import pytest

from sqlalchemy.orm import Session

from financial_pipeline.db.orm_models import RawApiIngestion
from financial_pipeline.db.repositories import RawApiIngestionRepository


pytestmark = pytest.mark.integration


def test_create_ingestion_persists_and_returns_raw_ingestion(
    db_session: Session,
) -> None:
    repository = RawApiIngestionRepository(db_session)

    request_parameters = {
        "base": "EUR",
        "quotes": "USD,GBP",
        "from": "2026-01-01",
        "to": "2026-01-31",
    }

    response_payload = [
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "USD",
            "rate": 1.1625,
        },
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "GBP",
            "rate": 0.8652,
        },
    ]

    payload_hash = "a" * 64

    ingestion = repository.create_ingestion(
        source_name="frankfurter",
        provider="ECB",
        request_parameters=request_parameters,
        response_payload=response_payload,
        payload_hash=payload_hash,
    )

    # 1. Verify the returned object.
    assert ingestion.ingestion_id is not None
    assert ingestion.fetched_at is not None

    assert ingestion.source_name == "frankfurter"
    assert ingestion.provider == "ECB"
    assert ingestion.request_parameters == request_parameters
    assert ingestion.response_payload == response_payload
    assert ingestion.payload_hash == payload_hash

    ingestion_id = ingestion.ingestion_id

    # 2. Expire the session cache.
    db_session.expire_all()

    # 3. Retrieve the record from PostgreSQL.
    persisted_ingestion = db_session.get(
        RawApiIngestion,
        ingestion_id,
    )

    # 4. Verify that the record actually exists.
    assert persisted_ingestion is not None
    assert persisted_ingestion.ingestion_id == ingestion_id
    assert persisted_ingestion.source_name == "frankfurter"
    assert persisted_ingestion.provider == "ECB"
    assert persisted_ingestion.request_parameters == request_parameters
    assert persisted_ingestion.response_payload == response_payload
    assert persisted_ingestion.payload_hash == payload_hash
    assert persisted_ingestion.fetched_at is not None