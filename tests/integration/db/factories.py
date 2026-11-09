from datetime import date
from decimal import Decimal

from financial_pipeline.db.orm_models import (
    RawApiIngestion,
    StagingExchangeRate,
)


def build_raw_api_ingestion(
    *,
    payload_hash: str = "a" * 64,
) -> RawApiIngestion:
    return RawApiIngestion(
        source_name="frankfurter",
        provider="ECB",
        request_parameters={
            "base": "EUR",
            "quotes": "USD,GBP",
            "from": "2026-01-01",
            "to": "2026-01-31",
        },
        response_payload=[
            {
                "date": "2026-01-15",
                "base": "EUR",
                "quote": "USD",
                "rate": "1.1625",
            }
        ],
        payload_hash=payload_hash,
    )


def build_exchange_rate(
    source_ingestion_id: int,
    *,
    rate_date: date = date(2026, 1, 15),
    base_currency: str = "EUR",
    quote_currency: str = "USD",
    provider: str = "ECB",
    rate: Decimal = Decimal("1.16250000"),
) -> StagingExchangeRate:
    return StagingExchangeRate(
        source_ingestion_id=source_ingestion_id,
        rate_date=rate_date,
        base_currency=base_currency,
        quote_currency=quote_currency,
        provider=provider,
        rate=rate,
    )