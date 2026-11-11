from datetime import date
from decimal import Decimal

import httpx
import pytest

from financial_pipeline.api.frankfurter_client import FrankfurterClient
from financial_pipeline.api.schemas import FrankfurterRateResponse
from financial_pipeline.config import Settings

BASE_URL = "https://api.frankfurter.dev/v2"
PROVIDER = "ECB"
DATABASE_URL = (
    "postgresql+psycopg://test_user:test_password@localhost:5432/test_database"
)


# Fake settings without loading the real .env file.
@pytest.fixture
def settings() -> Settings:
    """Build settings for the Frankfurter client tests."""
    return Settings(
        frankfurter_api_base_url=BASE_URL,
        frankfurter_provider=PROVIDER,
        database_url=DATABASE_URL,
    )


# Valid API response payload.
@pytest.fixture
def sample_rates() -> list[dict[str, str]]:
    return [
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "USD",
            "rate": "1.1625",
        },
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "GBP",
            "rate": "0.8650",
        },
    ]


# Verifies URL and query parameters.
def test_builds_expected_url_and_query_params(settings, sample_rates):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"

        assert str(request.url).split("?")[0] == (
            f"{BASE_URL}/providers/{PROVIDER}/rates"
        )

        assert dict(request.url.params) == {
            "base": "EUR",
            "quotes": "USD,GBP",
            "from": "2026-01-01",
            "to": "2026-01-31",
        }

        return httpx.Response(200, json=sample_rates)

    transport = httpx.MockTransport(handler)

    with httpx.Client(transport=transport) as http_client:
        client = FrankfurterClient(http_client, settings)

        client.get_rates(
            base_currency="EUR",
            quote_currencies=["USD", "GBP"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )


# Validates parsed response models.
def test_returns_raw_payload_and_validated_rate_responses(
    settings: Settings, sample_rates: list[dict[str, str]]
) -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=sample_rates)
    )

    with httpx.Client(transport=transport) as http_client:
        client = FrankfurterClient(http_client, settings)

        result = client.get_rates(
            base_currency="EUR",
            quote_currencies=["USD", "GBP"],
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )

    assert result.raw_payload == sample_rates
    assert len(result.rates) == 2

    assert isinstance(result.rates[0], FrankfurterRateResponse)
    assert all(isinstance(rate, FrankfurterRateResponse) for rate in result.rates)

    assert result.rates[0].base == "EUR"
    assert result.rates[0].quote == "USD"
    assert result.rates[0].rate == Decimal("1.1625")

    assert result.rates[1].quote == "GBP"
    assert result.rates[1].rate == Decimal("0.8650")


# Propagates HTTP status errors.
@pytest.mark.parametrize("status_code", [400, 404, 500, 503])
def test_propagates_http_status_error(settings, status_code):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code,
            json={"error": "Something went wrong"},
        )
    )

    with httpx.Client(transport=transport) as http_client:
        client = FrankfurterClient(http_client, settings)

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.get_rates(
                base_currency="EUR",
                quote_currencies=["USD"],
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )

    assert exc_info.value.response.status_code == status_code
