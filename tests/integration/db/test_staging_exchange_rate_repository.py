from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from financial_pipeline.api.schemas import FrankfurterRateResponse
from financial_pipeline.db.orm_models import (
    RawApiIngestion,
    StagingExchangeRate,
)
from financial_pipeline.db.repositories import StagingExchangeRateRepository

pytestmark = pytest.mark.integration


def test_insert_rates_if_absent_persists_validated_rates(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    # Arrange
    repository = StagingExchangeRateRepository(session=db_session)

    rates = [
        FrankfurterRateResponse(
            date=date(2026, 1, 15),
            base="EUR",
            quote="USD",
            rate=Decimal("1.1625"),
        ),
        FrankfurterRateResponse(
            date=date(2026, 1, 15),
            base="EUR",
            quote="GBP",
            rate=Decimal("0.8652"),
        ),
    ]

    # Act
    inserted_count = repository.insert_rates_if_absent(
        source_ingestion_id=persisted_raw_ingestion.ingestion_id,
        provider="ECB",
        rates=rates,
    )

    # Assert
    assert inserted_count == 2

    db_session.flush()
    db_session.expire_all()

    statement = (
        select(StagingExchangeRate)
        .where(
            StagingExchangeRate.source_ingestion_id
            == persisted_raw_ingestion.ingestion_id
        )
        .order_by(StagingExchangeRate.quote_currency)
    )

    persisted_rates = db_session.scalars(statement).all()

    assert len(persisted_rates) == 2

    gbp_rate, usd_rate = persisted_rates

    assert usd_rate.source_ingestion_id == persisted_raw_ingestion.ingestion_id
    assert usd_rate.rate_date == date(2026, 1, 15)
    assert usd_rate.base_currency == "EUR"
    assert usd_rate.quote_currency == "USD"
    assert usd_rate.provider == "ECB"
    assert usd_rate.rate == Decimal("1.1625")

    assert gbp_rate.source_ingestion_id == persisted_raw_ingestion.ingestion_id
    assert gbp_rate.rate_date == date(2026, 1, 15)
    assert gbp_rate.base_currency == "EUR"
    assert gbp_rate.quote_currency == "GBP"
    assert gbp_rate.provider == "ECB"
    assert gbp_rate.rate == Decimal("0.8652")


def test_insert_rates_if_absent_returns_zero_for_empty_rates(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
) -> None:
    repository = StagingExchangeRateRepository(session=db_session)

    inserted_count = repository.insert_rates_if_absent(
        source_ingestion_id=persisted_raw_ingestion.ingestion_id,
        provider="ECB",
        rates=[],
    )

    assert inserted_count == 0


def test_insert_rates_if_absent_ignores_existing_natural_keys(
    db_session: Session,
    persisted_raw_ingestion: RawApiIngestion,
    raw_ingestion_factory: Callable[..., RawApiIngestion],
) -> None:
    # Arrange
    repository = StagingExchangeRateRepository(session=db_session)

    rate = FrankfurterRateResponse(
        date=date(2026, 1, 15),
        base="EUR",
        quote="USD",
        rate=Decimal("1.1625"),
    )

    first_ingestion_id = persisted_raw_ingestion.ingestion_id

    # Insert the rate using the first ingestion.
    first_inserted_count = repository.insert_rates_if_absent(
        source_ingestion_id=first_ingestion_id,
        provider="ECB",
        rates=[rate],
    )

    assert first_inserted_count == 1

    # Create a second raw ingestion.
    second_ingestion = raw_ingestion_factory()
    second_ingestion_id = second_ingestion.ingestion_id

    assert second_ingestion_id != first_ingestion_id

    # Act: attempt to insert the same natural key.
    second_inserted_count = repository.insert_rates_if_absent(
        source_ingestion_id=second_ingestion_id,
        provider="ECB",
        rates=[rate],
    )

    # Assert
    assert second_inserted_count == 0

    db_session.flush()
    db_session.expire_all()

    statement = select(StagingExchangeRate).where(
        StagingExchangeRate.rate_date == date(2026, 1, 15),
        StagingExchangeRate.base_currency == "EUR",
        StagingExchangeRate.quote_currency == "USD",
        StagingExchangeRate.provider == "ECB",
    )

    persisted_rates = db_session.scalars(statement).all()

    assert len(persisted_rates) == 1

    persisted_rate = persisted_rates[0]

    assert persisted_rate.source_ingestion_id == first_ingestion_id
    assert persisted_rate.source_ingestion_id != second_ingestion_id
    assert persisted_rate.rate == Decimal("1.1625")
