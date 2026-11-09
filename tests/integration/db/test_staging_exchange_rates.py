from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session, selectinload

from financial_pipeline.db.orm_models import (
    RawApiIngestion,
    StagingExchangeRate,
)
from factories import build_exchange_rate


pytestmark = pytest.mark.integration


def test_persists_exchange_rate(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    exchange_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
    )

    db_session.add(exchange_rate)
    db_session.flush()

    exchange_rate_id = exchange_rate.exchange_rate_id

    db_session.expire_all()

    result = db_session.get(
        StagingExchangeRate,
        exchange_rate_id,
    )

    assert result is not None
    assert result.source_ingestion_id == persisted_raw_ingestion.ingestion_id
    assert result.rate_date == date(2026, 1, 15)
    assert result.base_currency == "EUR"
    assert result.quote_currency == "USD"
    assert result.provider == "ECB"
    assert result.rate == Decimal("1.16250000")
    assert result.ingested_at is not None


def test_persists_relationship_between_ingestion_and_rates(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    persisted_raw_ingestion.exchange_rates = [
        StagingExchangeRate(
            rate_date=date(2026, 1, 15),
            base_currency="EUR",
            quote_currency="USD",
            provider="ECB",
            rate=Decimal("1.16250000"),
        ),
        StagingExchangeRate(
            rate_date=date(2026, 1, 15),
            base_currency="EUR",
            quote_currency="GBP",
            provider="ECB",
            rate=Decimal("0.86500000"),
        ),
    ]

    db_session.flush()
    db_session.expire_all()

    result = db_session.scalar(
        select(RawApiIngestion)
        .options(selectinload(RawApiIngestion.exchange_rates))
        .where(
            RawApiIngestion.ingestion_id
            == persisted_raw_ingestion.ingestion_id
        )
    )

    assert result is not None
    assert len(result.exchange_rates) == 2

    assert {
        exchange_rate.quote_currency
        for exchange_rate in result.exchange_rates
    } == {"USD", "GBP"}

    assert all(
        exchange_rate.source_ingestion_id == result.ingestion_id
        for exchange_rate in result.exchange_rates
    )


@pytest.mark.parametrize(
    "invalid_currency",
    [
        "EU",
        "US1",
        "123",
        "eur",
    ],
)
def test_rejects_invalid_base_currency(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
    invalid_currency: str,
) -> None:
    exchange_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
        base_currency=invalid_currency,
    )

    db_session.add(exchange_rate)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


@pytest.mark.parametrize(
    "invalid_currency",
    [
        "US",
        "123",
        "usd",
    ],
)
def test_rejects_invalid_quote_currency(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
    invalid_currency: str,
) -> None:
    exchange_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
        quote_currency=invalid_currency,
    )

    db_session.add(exchange_rate)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_rejects_same_base_and_quote_currency(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    exchange_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
        base_currency="EUR",
        quote_currency="EUR",
    )

    db_session.add(exchange_rate)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


@pytest.mark.parametrize(
    "invalid_rate",
    [
        Decimal("0"),
        Decimal("-1"),
        Decimal("-0.5"),
    ],
)
def test_rejects_zero_or_negative_rate(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
    invalid_rate: Decimal,
) -> None:
    exchange_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
        rate=invalid_rate,
    )

    db_session.add(exchange_rate)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_rejects_duplicate_exchange_rate(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    first_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
    )
    second_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
    )

    db_session.add(first_rate)
    db_session.flush()

    db_session.add(second_rate)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_rejects_nonexistent_source_ingestion(
    db_session: Session,
) -> None:
    exchange_rate = build_exchange_rate(
        source_ingestion_id=999_999_999,
    )

    db_session.add(exchange_rate)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_rejects_base_currency_longer_than_column_limit(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    exchange_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
        base_currency="EURO",
    )

    db_session.add(exchange_rate)

    with pytest.raises(DataError):
        db_session.flush()

    db_session.rollback()

def test_rejects_quote_currency_longer_than_column_limit(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    exchange_rate = build_exchange_rate(
        persisted_raw_ingestion.ingestion_id,
        quote_currency="USD1",
    )

    db_session.add(exchange_rate)

    with pytest.raises(DataError):
        db_session.flush()

    db_session.rollback()
