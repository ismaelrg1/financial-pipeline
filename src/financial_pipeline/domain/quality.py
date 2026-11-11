from collections.abc import Sequence
from datetime import date

from financial_pipeline.api.schemas import FrankfurterRateResponse


class ExchangeRateQualityError(ValueError):
    """Raised when fetched exchange rates violate quality rules."""


def validate_exchange_rate_coverage(
    *,
    rates: Sequence[FrankfurterRateResponse],
    expected_base_currency: str,
    expected_quote_currencies: Sequence[str],
) -> None:

    if not rates:
        raise ExchangeRateQualityError("No exchange rates were returned")

    expected_quotes = set(expected_quote_currencies)
    observed_quotes: dict[date, set[str]] = {}
    seen_rate_keys: set[tuple[date, str, str]] = set()

    for rate in rates:
        if rate.base != expected_base_currency:
            raise ExchangeRateQualityError(f"Unexpected base currency: {rate.base}")

        key = (rate.date, rate.base, rate.quote)

        if key in seen_rate_keys:
            raise ExchangeRateQualityError(
                f"Duplicate exchange rate for {rate.date} {rate.base}/{rate.quote}"
            )

        seen_rate_keys.add(key)

        if rate.date not in observed_quotes:
            observed_quotes[rate.date] = set()

        observed_quotes[rate.date].add(rate.quote)

    for rate_date, rate_quotes in observed_quotes.items():
        unexpected_quotes = rate_quotes - expected_quotes

        if unexpected_quotes:
            unexpected_quotes_text = ", ".join(sorted(unexpected_quotes))
            raise ExchangeRateQualityError(
                f"Unexpected quote currencies for {rate_date}: {unexpected_quotes_text}"
            )

        missing_quotes = expected_quotes - rate_quotes

        if missing_quotes:
            missing_quotes_text = ", ".join(sorted(missing_quotes))
            raise ExchangeRateQualityError(
                f"Incomplete quote coverage for {rate_date}: missing {missing_quotes_text}"
            )
