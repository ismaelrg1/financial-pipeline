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


def test_daily_exchange_rate_metrics_partitions_rates_by_currency(
    db_session: Session,
) -> None:
    # 1. Create a raw ingestion
    raw_ingestion = RawApiIngestion(
        source_name="frankfurter",
        provider="test_partition",
        request_parameters={
            "base": "EUR",
            "quotes": "USD,GBP",
            "from": "2026-01-12",
            "to": "2026-01-13",
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
                "date": "2026-01-13",
                "base": "EUR",
                "quote": "GBP",
                "rate": 0.8600,
            },
        ],
        payload_hash="b" * 64,
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
            provider="test_partition",
            rate=Decimal("1.0000"),
        ),
        StagingExchangeRate(
            source_ingestion_id=raw_ingestion.ingestion_id,
            rate_date=date(2026, 1, 13),
            base_currency="EUR",
            quote_currency="USD",
            provider="test_partition",
            rate=Decimal("1.1000"),
        ),
        StagingExchangeRate(
            source_ingestion_id=raw_ingestion.ingestion_id,
            rate_date=date(2026, 1, 13),
            base_currency="EUR",
            quote_currency="GBP",
            provider="test_partition",
            rate=Decimal("0.8600"),
        ),
    ]

    db_session.add_all(staging_rates)
    db_session.flush()

    # 3. Query the mart view
    statement = text(
        """
        SELECT
            rate_date,
            quote_currency,
            rate,
            previous_rate,
            absolute_change,
            percentage_change
        FROM mart.daily_exchange_rate_metrics
        WHERE base_currency = 'EUR'
          AND provider = 'test_partition'
        ORDER BY rate_date, quote_currency;
        """
    )

    results = db_session.execute(statement).mappings().all()

    # 4. Verify the results
    assert len(results) == 3

    usd_previous_day, gbp_current_day, usd_current_day = results

    # EUR/USD on 2026-01-12: first available rate
    assert usd_previous_day["rate_date"] == date(2026, 1, 12)
    assert usd_previous_day["quote_currency"] == "USD"
    assert usd_previous_day["previous_rate"] is None
    assert usd_previous_day["absolute_change"] is None
    assert usd_previous_day["percentage_change"] is None

    # EUR/GBP on 2026-01-13: independent partition
    assert gbp_current_day["rate_date"] == date(2026, 1, 13)
    assert gbp_current_day["quote_currency"] == "GBP"
    assert gbp_current_day["previous_rate"] is None
    assert gbp_current_day["absolute_change"] is None
    assert gbp_current_day["percentage_change"] is None

    # EUR/USD on 2026-01-13: previous USD rate is used
    assert usd_current_day["rate_date"] == date(2026, 1, 13)
    assert usd_current_day["quote_currency"] == "USD"
    assert usd_current_day["previous_rate"] == Decimal("1.00000000")
    assert usd_current_day["absolute_change"] == Decimal("0.10000000")
    assert usd_current_day["percentage_change"] == Decimal("10")
