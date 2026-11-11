import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from financial_pipeline.api.frankfurter_client import FrankfurterClient
from financial_pipeline.db.repositories import (
    RawApiIngestionRepository,
    StagingExchangeRateRepository,
)
from financial_pipeline.domain.quality import validate_exchange_rate_coverage

FRANKFURTER_SOURCE_NAME = "frankfurter"


@dataclass(frozen=True)
class ExchangeRateIngestionResult:
    ingestion_id: int
    fetched_rate_count: int
    inserted_rate_count: int


def calculate_payload_hash(
    payload: list[dict[str, object]],
) -> str:
    """Return a deterministic SHA-256 hash for a JSON API payload."""
    serialized_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    payload_bytes = serialized_payload.encode("utf-8")

    return hashlib.sha256(payload_bytes).hexdigest()


def ingest_exchange_rates(
    *,
    client: FrankfurterClient,
    session_factory: sessionmaker[Session],
    provider: str,
    base_currency: str,
    quote_currencies: Sequence[str],
    start_date: date,
    end_date: date,
) -> ExchangeRateIngestionResult:
    """Fetch, persist, and stage exchange rates in one transaction."""

    # 1. Fetch data from Frankfurter.
    fetched_rates = client.get_rates(
        base_currency=base_currency,
        quote_currencies=quote_currencies,
        start_date=start_date,
        end_date=end_date,
    )

    # 1.5. Validate the exchange-rate coverage contract.
    validate_exchange_rate_coverage(
        rates=fetched_rates.rates,
        expected_base_currency=base_currency,
        expected_quote_currencies=quote_currencies,
    )

    # 2. Build request metadata.
    request_parameters = {
        "base": base_currency,
        "quotes": ",".join(quote_currencies),
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
    }

    # 3. Calculate payload hash.
    payload_hash = calculate_payload_hash(fetched_rates.raw_payload)

    # 4. Persist raw ingestion and staging rates atomically.
    with session_factory.begin() as session:
        raw_repository = RawApiIngestionRepository(session=session)

        staging_repository = StagingExchangeRateRepository(session=session)

        ingestion = raw_repository.create_ingestion(
            source_name=FRANKFURTER_SOURCE_NAME,
            provider=provider,
            request_parameters=request_parameters,
            response_payload=fetched_rates.raw_payload,
            payload_hash=payload_hash,
        )

        ingestion_id = ingestion.ingestion_id

        # Insert staging exchange rates.
        inserted_rate_count = staging_repository.insert_rates_if_absent(
            source_ingestion_id=ingestion_id,
            provider=provider,
            rates=fetched_rates.rates,
        )

        # Build result.
        result = ExchangeRateIngestionResult(
            ingestion_id=ingestion_id,
            fetched_rate_count=len(fetched_rates.rates),
            inserted_rate_count=inserted_rate_count,
        )

    return result
