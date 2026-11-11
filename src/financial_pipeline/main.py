import argparse
import logging
from collections.abc import Sequence
from datetime import date

import httpx
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from financial_pipeline.api.frankfurter_client import FrankfurterClient
from financial_pipeline.config import Settings
from financial_pipeline.db.session import create_database_engine, create_session_factory
from financial_pipeline.domain.quality import ExchangeRateQualityError
from financial_pipeline.logging_config import configure_logging
from financial_pipeline.pipeline.exchange_rates import ingest_exchange_rates

logger = logging.getLogger(__name__)


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date: {value}. Expected format: YYYY-MM-DD."
        ) from exc


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Financial data pipeline for exchange rates."
    )

    parser.add_argument(
        "--start-date",
        type=parse_iso_date,
        required=True,
        help="Start date in ISO format (YYYY-MM-DD).",
    )

    parser.add_argument(
        "--end-date",
        type=parse_iso_date,
        required=True,
        help="End date in ISO format (YYYY-MM-DD).",
    )

    return parser


def validate_date_range(
    start_date: date,
    end_date: date,
) -> None:
    if end_date < start_date:
        raise ValueError(
            "end_date must be on or after start_date",
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()

    arguments = parser.parse_args(argv)

    try:
        validate_date_range(
            arguments.start_date,
            arguments.end_date,
        )
    except ValueError as error:
        parser.error(str(error))
        return 2

    settings = Settings()  # pyright: ignore[reportCallIssue]  # Loaded from environment.

    configure_logging(settings.log_level)

    engine = create_database_engine(settings.database_url)

    session_factory = create_session_factory(engine)

    try:
        with httpx.Client(timeout=settings.http_timeout_seconds) as http_client:
            client = FrankfurterClient(
                http_client=http_client,
                settings=settings,
            )

            result = ingest_exchange_rates(
                client=client,
                session_factory=session_factory,
                provider=settings.frankfurter_provider,
                base_currency=settings.frankfurter_base_currency,
                quote_currencies=settings.frankfurter_quote_currencies,
                start_date=arguments.start_date,
                end_date=arguments.end_date,
            )

        logger.info(
            "Pipeline completed | ingestion_id=%s "
            "fetched_rate_count=%s inserted_rate_count=%s",
            result.ingestion_id,
            result.fetched_rate_count,
            result.inserted_rate_count,
        )

        return 0
    except (
        httpx.HTTPError,
        ValidationError,
        SQLAlchemyError,
        ExchangeRateQualityError,
    ):
        logger.exception("Pipeline failed")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
