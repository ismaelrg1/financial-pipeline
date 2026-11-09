from sqlalchemy.orm import Session

from financial_pipeline.db.orm_models import RawApiIngestion

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
