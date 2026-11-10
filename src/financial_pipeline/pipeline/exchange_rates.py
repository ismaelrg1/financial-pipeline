from collections.abc import Sequence
from datetime import date
import hashlib
import json

from sqlalchemy.orm import Session, sessionmaker

from financial_pipeline.api.frankfurter_client import FrankfurterClient
from financial_pipeline.db.repositories import RawApiIngestionRepository


FRANKFURTER_SOURCE_NAME = "frankfurter"


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


def ingest_raw_exchange_rates(
    *,
    client: FrankfurterClient,
    session_factory: sessionmaker[Session],
    provider: str,
    base_currency: str,
    quote_currencies: Sequence[str],
    start_date: date,
    end_date: date,
) -> int:

    fetched_rates = client.get_rates(
        base_currency=base_currency,
        quote_currencies=quote_currencies,
        start_date=start_date,
        end_date=end_date,
    )

    request_parameters = {
        "base": base_currency,
        "quotes": ",".join(quote_currencies),
        "from": start_date.isoformat(),
        "to": end_date.isoformat(),
    }

    payload_hash = calculate_payload_hash(
        fetched_rates.raw_payload
    )

    with session_factory.begin() as session:
        repository = RawApiIngestionRepository(session=session)

        ingestion = repository.create_ingestion(
            source_name=FRANKFURTER_SOURCE_NAME,
            provider=provider,
            request_parameters=request_parameters,
            response_payload=fetched_rates.raw_payload,
            payload_hash=payload_hash,
        )

        ingestion_id = ingestion.ingestion_id

    return ingestion_id
