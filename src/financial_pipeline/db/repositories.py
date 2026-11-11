from collections.abc import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from financial_pipeline.api.schemas import FrankfurterRateResponse
from financial_pipeline.db.orm_models import RawApiIngestion, StagingExchangeRate


class RawApiIngestionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_ingestion(
        self,
        *,
        source_name: str,
        provider: str,
        request_parameters: dict[str, str],
        response_payload: list[dict[str, object]],
        payload_hash: str,
    ) -> RawApiIngestion:

        raw_api_ingestion = RawApiIngestion(
            source_name=source_name,
            provider=provider,
            request_parameters=request_parameters,
            response_payload=response_payload,
            payload_hash=payload_hash,
        )

        self._session.add(raw_api_ingestion)
        self._session.flush()

        return raw_api_ingestion


class StagingExchangeRateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_rates_if_absent(
        self,
        *,
        source_ingestion_id: int,
        provider: str,
        rates: Sequence[FrankfurterRateResponse],
    ) -> int:
        if not rates:
            return 0

        values = [
            {
                "source_ingestion_id": source_ingestion_id,
                "rate_date": rate.date,
                "base_currency": rate.base,
                "quote_currency": rate.quote,
                "provider": provider,
                "rate": rate.rate,
            }
            for rate in rates
        ]

        statement = (
            insert(StagingExchangeRate)
            .values(values)
            .on_conflict_do_nothing(
                constraint="uq_exchange_rates_rate_date_base_quote_provider"
            )
            .returning(StagingExchangeRate.exchange_rate_id)
        )

        result = self._session.execute(statement)

        return len(result.scalars().all())
