from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from financial_pipeline.db.orm_models import (
    RawApiIngestion,
    StagingExchangeRate,
)

pytestmark = pytest.mark.integration


def test_daily_exchange_rate_metrics_calculates_changes(
    db_session: Session,
) -> None:
    # 1. Create a raw ingestion
    raw_ingestion = RawApiIngestion(
        source_name="frankfurter",
        provider="test",
        request_parameters={
            "base": "EUR",
            "quotes": "USD",
            "from": "2026-01-12",
            "to": "2026-01-14",
        },
        response_payload=[
            {
                "date": "2026-01-12",
                "base": "EUR",
                "quote": "USD",
                "rate": 1.0000,
            },
            {
                "date": "2026-01-13",
                "base": "EUR",
                "quote": "USD",
                "rate": 1.1000,
            },
            {
                "date": "2026-01-14",
                "base": "EUR",
                "quote": "USD",
                "rate": 1.0450,
            },
        ],
        payload_hash="a" * 64,
    )

    db_session.add(raw_ingestion)
    db_session.flush()

    # 2. Insert staging exchange rates
    staging_rates = [
        StagingExchangeRate(
            source_ingestion_id=raw_ingestion.ingestion_id,
            rate_date=date(2026, 1, 12),
            base_currency="EUR",
            quote_currency="USD",
            provider="test",
            rate=Decimal("1.0000"),
        ),
        StagingExchangeRate(
            source_ingestion_id=raw_ingestion.ingestion_id,
            rate_date=date(2026, 1, 13),
            base_currency="EUR",
            quote_currency="USD",
            provider="test",
            rate=Decimal("1.1000"),
        ),
        StagingExchangeRate(
            source_ingestion_id=raw_ingestion.ingestion_id,
            rate_date=date(2026, 1, 14),
            base_currency="EUR",
            quote_currency="USD",
            provider="test",
            rate=Decimal("1.0450"),
        ),
    ]

    db_session.add_all(staging_rates)
    db_session.flush()

    # 3. Query the mart view
    statement = text(
        """
        SELECT
            rate_date,
            rate,
            previous_rate,
            absolute_change,
            percentage_change
        FROM mart.daily_exchange_rate_metrics
        WHERE base_currency = 'EUR'
          AND quote_currency = 'USD'
          AND provider = 'test'
        ORDER BY rate_date;
        """
    )

    results = db_session.execute(statement).mappings().all()

    # 4. Verify the results
    assert len(results) == 3

    first_day, second_day, third_day = results

    # 2026-01-12: First available rate
    assert first_day["rate_date"] == date(2026, 1, 12)
    assert first_day["rate"] == Decimal("1.00000000")
    assert first_day["previous_rate"] is None
    assert first_day["absolute_change"] is None
    assert first_day["percentage_change"] is None

    # 2026-01-13: Positive change
    assert second_day["rate_date"] == date(2026, 1, 13)
    assert second_day["rate"] == Decimal("1.10000000")
    assert second_day["previous_rate"] == Decimal("1.00000000")
    assert second_day["absolute_change"] == Decimal("0.10000000")
    assert second_day["percentage_change"] == Decimal(10)

    # 2026-01-14: Negative change
    assert third_day["rate_date"] == date(2026, 1, 14)
    assert third_day["rate"] == Decimal("1.04500000")
    assert third_day["previous_rate"] == Decimal("1.10000000")
    assert third_day["absolute_change"] == Decimal("-0.05500000")
    assert third_day["percentage_change"] == Decimal(-5)
