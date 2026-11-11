import argparse
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import httpx
import pytest

import financial_pipeline.main as main_module
from financial_pipeline.domain.quality import ExchangeRateQualityError
from financial_pipeline.main import (
    build_argument_parser,
    parse_iso_date,
    validate_date_range,
)


def test_parse_iso_date_returns_date() -> None:
    result = parse_iso_date("2026-01-15")

    assert result == date(2026, 1, 15)


def test_parse_iso_date_raises_argument_type_error_for_invalid_date() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_iso_date("15/01/2026")


def test_argument_parser_accepts_valid_dates() -> None:
    parser = build_argument_parser()

    args = parser.parse_args(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-15",
        ]
    )

    assert args.start_date == date(2026, 1, 1)
    assert args.end_date == date(2026, 1, 15)


def test_validate_date_range_rejects_end_date_before_start_date() -> None:
    with pytest.raises(
        ValueError,
        match="end_date must be on or after start_date",
    ):
        validate_date_range(
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 1),
        )


def test_validate_date_range_accepts_equal_dates() -> None:
    validate_date_range(
        start_date=date(2026, 1, 15),
        end_date=date(2026, 1, 15),
    )


def configure_main_dependencies(monkeypatch):
    """Replace external dependencies used by main() with mocks."""

    settings = SimpleNamespace(
        log_level="INFO",
        database_url="postgresql://test:test@localhost/test",
        http_timeout_seconds=10,
        frankfurter_provider="ECB",
        frankfurter_base_currency="EUR",
        frankfurter_quote_currencies=["USD", "GBP"],
    )

    engine = Mock()
    session_factory = Mock()

    http_client = Mock()
    http_context = MagicMock()
    http_context.__enter__.return_value = http_client

    frankfurter_client = Mock()

    monkeypatch.setattr(
        main_module,
        "Settings",
        Mock(return_value=settings),
    )
    monkeypatch.setattr(
        main_module,
        "configure_logging",
        Mock(),
    )
    monkeypatch.setattr(
        main_module,
        "create_database_engine",
        Mock(return_value=engine),
    )
    monkeypatch.setattr(
        main_module,
        "create_session_factory",
        Mock(return_value=session_factory),
    )
    monkeypatch.setattr(
        main_module.httpx,
        "Client",
        Mock(return_value=http_context),
    )
    monkeypatch.setattr(
        main_module,
        "FrankfurterClient",
        Mock(return_value=frankfurter_client),
    )

    return {
        "settings": settings,
        "engine": engine,
        "session_factory": session_factory,
        "http_client": http_client,
        "frankfurter_client": frankfurter_client,
    }


def test_main_returns_zero_when_pipeline_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies = configure_main_dependencies(monkeypatch)

    pipeline_result = SimpleNamespace(
        ingestion_id=1,
        fetched_rate_count=2,
        inserted_rate_count=2,
    )

    ingest_mock = Mock(return_value=pipeline_result)
    monkeypatch.setattr(
        main_module,
        "ingest_exchange_rates",
        ingest_mock,
    )

    result = main_module.main(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-15",
        ]
    )

    assert result == 0

    ingest_mock.assert_called_once_with(
        client=dependencies["frankfurter_client"],
        session_factory=dependencies["session_factory"],
        provider="ECB",
        base_currency="EUR",
        quote_currencies=["USD", "GBP"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 15),
    )

    dependencies["engine"].dispose.assert_called_once()


def test_main_returns_one_when_http_request_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies = configure_main_dependencies(monkeypatch)

    ingest_mock = Mock(side_effect=httpx.ConnectError("Connection failed"))
    monkeypatch.setattr(
        main_module,
        "ingest_exchange_rates",
        ingest_mock,
    )

    result = main_module.main(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-15",
        ]
    )

    assert result == 1

    ingest_mock.assert_called_once_with(
        client=dependencies["frankfurter_client"],
        session_factory=dependencies["session_factory"],
        provider="ECB",
        base_currency="EUR",
        quote_currencies=["USD", "GBP"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 15),
    )

    dependencies["engine"].dispose.assert_called_once()


def test_main_exits_with_code_two_when_date_range_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_mock = Mock()
    monkeypatch.setattr(
        main_module,
        "Settings",
        settings_mock,
    )

    with pytest.raises(SystemExit) as exc_info:
        main_module.main(
            [
                "--start-date",
                "2026-01-15",
                "--end-date",
                "2026-01-01",
            ]
        )

    assert exc_info.value.code == 2

    # The application must reject the dates before initializing dependencies.
    settings_mock.assert_not_called()


def test_main_returns_one_when_exchange_rate_quality_validation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependencies = configure_main_dependencies(monkeypatch)

    ingest_mock = Mock(
        side_effect=ExchangeRateQualityError("No exchange rates were returned")
    )
    monkeypatch.setattr(
        main_module,
        "ingest_exchange_rates",
        ingest_mock,
    )

    result = main_module.main(
        [
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
        ]
    )

    assert result == 1

    ingest_mock.assert_called_once_with(
        client=dependencies["frankfurter_client"],
        session_factory=dependencies["session_factory"],
        provider="ECB",
        base_currency="EUR",
        quote_currencies=["USD", "GBP"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    dependencies["engine"].dispose.assert_called_once()
