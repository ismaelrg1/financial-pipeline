from datetime import date
from decimal import Decimal

import pytest

from financial_pipeline.api.schemas import FrankfurterRateResponse
from financial_pipeline.domain.quality import (
    ExchangeRateQualityError,
    validate_exchange_rate_coverage,
)


def make_rate(
    *,
    rate_date: date,
    base: str = "EUR",
    quote: str,
    rate: str = "1.0000",
) -> FrankfurterRateResponse:
    return FrankfurterRateResponse(
        date=rate_date,
        base=base,
        quote=quote,
        rate=Decimal(rate),
    )


def test_validate_exchange_rate_coverage_accepts_complete_dataset() -> None:
    rates = [
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="USD",
            rate="1.1600",
        ),
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="GBP",
            rate="0.8600",
        ),
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="JPY",
            rate="184.0000",
        ),
        make_rate(
            rate_date=date(2026, 1, 13),
            quote="USD",
            rate="1.1700",
        ),
        make_rate(
            rate_date=date(2026, 1, 13),
            quote="GBP",
            rate="0.8700",
        ),
        make_rate(
            rate_date=date(2026, 1, 13),
            quote="JPY",
            rate="185.0000",
        ),
    ]

    validate_exchange_rate_coverage(
        rates=rates,
        expected_base_currency="EUR",
        expected_quote_currencies=["USD", "GBP", "JPY"],
    )


def test_validate_exchange_rate_coverage_rejects_empty_dataset() -> None:
    with pytest.raises(
        ExchangeRateQualityError,
        match="No exchange rates were returned",
    ):
        validate_exchange_rate_coverage(
            rates=[],
            expected_base_currency="EUR",
            expected_quote_currencies=["USD", "GBP", "JPY"],
        )


def test_validate_exchange_rate_coverage_rejects_missing_quote_currency() -> None:
    rates = [
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="USD",
        ),
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="GBP",
        ),
        # JPY is missing on 2026-01-12.
        make_rate(
            rate_date=date(2026, 1, 13),
            quote="USD",
        ),
        make_rate(
            rate_date=date(2026, 1, 13),
            quote="GBP",
        ),
        make_rate(
            rate_date=date(2026, 1, 13),
            quote="JPY",
        ),
    ]

    with pytest.raises(
        ExchangeRateQualityError,
        match="Incomplete quote coverage for 2026-01-12: missing JPY",
    ):
        validate_exchange_rate_coverage(
            rates=rates,
            expected_base_currency="EUR",
            expected_quote_currencies=["USD", "GBP", "JPY"],
        )


def test_validate_exchange_rate_coverage_rejects_unexpected_quote_currency() -> None:
    rates = [
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="USD",
        ),
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="GBP",
        ),
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="JPY",
        ),
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="CHF",
        ),
    ]

    with pytest.raises(
        ExchangeRateQualityError,
        match="Unexpected quote currencies for 2026-01-12: CHF",
    ):
        validate_exchange_rate_coverage(
            rates=rates,
            expected_base_currency="EUR",
            expected_quote_currencies=["USD", "GBP", "JPY"],
        )


def test_validate_exchange_rate_coverage_rejects_unexpected_base_currency() -> None:
    rates = [
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="USD",
            base="USD",
        ),
    ]

    with pytest.raises(
        ExchangeRateQualityError,
        match="Unexpected base currency: USD",
    ):
        validate_exchange_rate_coverage(
            rates=rates,
            expected_base_currency="EUR",
            expected_quote_currencies=["USD"],
        )


def test_validate_exchange_rate_coverage_rejects_duplicate_rates() -> None:
    rates = [
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="USD",
        ),
        make_rate(
            rate_date=date(2026, 1, 12),
            quote="USD",
            rate="1.1000",
        ),
    ]

    with pytest.raises(
        ExchangeRateQualityError,
        match="Duplicate exchange rate for 2026-01-12 EUR/USD",
    ):
        validate_exchange_rate_coverage(
            rates=rates,
            expected_base_currency="EUR",
            expected_quote_currencies=["USD"],
        )
