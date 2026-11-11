from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from financial_pipeline.api.schemas import FrankfurterRateResponse


def build_rate_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "date": "2026-01-15",
        "base": "EUR",
        "quote": "USD",
        "rate": "1.1625",
    }
    payload.update(overrides)
    return payload


# test de date y decimal
@pytest.mark.parametrize(
    ("raw_rate", "expected_rate"),
    [
        ("1.1625", Decimal("1.1625")),
        (1.1625, Decimal("1.1625")),
    ],
)
def test_converts_date_and_rate_types(
    raw_rate: str | float, expected_rate: Decimal
) -> None:
    result = FrankfurterRateResponse.model_validate(build_rate_payload(rate=raw_rate))

    assert result.date == date(2026, 1, 15)
    assert isinstance(result.date, date)

    assert result.rate == expected_rate
    assert isinstance(result.rate, Decimal)


# test normalizacion EUR/USD...
@pytest.mark.parametrize(
    ("base", "quote", "expected_base", "expected_quote"),
    [
        ("eur", "usd", "EUR", "USD"),
        ("Eur", "Usd", "EUR", "USD"),
        (" gbp ", " eur ", "GBP", "EUR"),
    ],
)
def test_normalizes_currency_codes(
    base: str,
    quote: str,
    expected_base: str,
    expected_quote: str,
) -> None:

    result = FrankfurterRateResponse.model_validate(
        build_rate_payload(base=base, quote=quote),
    )

    assert result.base == expected_base
    assert result.quote == expected_quote


# test de decimales negativos:
@pytest.mark.parametrize("rate", ["0", "0.0", "-1", "-0.5", None])
def test_rejects_zero_or_negative_rate(rate: str | None) -> None:

    with pytest.raises(ValidationError):
        FrankfurterRateResponse.model_validate(
            build_rate_payload(rate=rate),
        )


def test_rejects_missing_rate_field() -> None:
    payload = build_rate_payload()
    payload.pop("rate")

    with pytest.raises(ValidationError):
        FrankfurterRateResponse.model_validate(payload)


def test_rejects_invalid_date() -> None:
    with pytest.raises(ValidationError):
        FrankfurterRateResponse.model_validate(
            build_rate_payload(date="not-a-date"),
        )


# test codigo moneda invalido
@pytest.mark.parametrize(
    ("field_name", "currency"),
    [
        ("base", "EU"),
        ("base", "EURO"),
        ("base", "US1"),
        ("quote", "US$"),
        ("quote", "123"),
        ("quote", ""),
    ],
)
def test_rejects_invalid_currency_codes(
    field_name: str,
    currency: str,
) -> None:

    with pytest.raises(ValidationError):
        FrankfurterRateResponse.model_validate(
            build_rate_payload(**{field_name: currency}),
        )


def test_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        FrankfurterRateResponse.model_validate(
            build_rate_payload(unexpected_field="value"),
        )
