from datetime import date

import pytest
from sqlalchemy.engine import Engine


from unittest.mock import Mock

from financial_pipeline.api.frankfurter_client import FrankfurterClient
from financial_pipeline.db.orm_models import RawApiIngestion
from financial_pipeline.db.session import create_session_factory
from financial_pipeline.pipeline.exchange_rates import (
    FRANKFURTER_SOURCE_NAME,
    calculate_payload_hash,
    ingest_raw_exchange_rates,
)
from financial_pipeline.api.schemas import (
    FrankfurterRateResponse,
    FrankfurterRatesFetch,
)

pytestmark = pytest.mark.integration


def test_ingest_raw_exchange_rates_persists_ingestion(engine: Engine) -> None:
    # Arrange: preparar una respuesta simulada de Frankfurter.
    raw_payload = [
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "USD",
            "rate": 1.1625,
        },
        {
            "date": "2026-01-15",
            "base": "EUR",
            "quote": "GBP",
            "rate": 0.8652,
        },
    ]

    validated_rates = [
        FrankfurterRateResponse.model_validate(rate)
        for rate in raw_payload
    ]

    client = Mock(spec=FrankfurterClient)

    client.get_rates.return_value = FrankfurterRatesFetch(
        raw_payload=raw_payload,
        rates=validated_rates,
    )

    session_factory = create_session_factory(engine)

    # Act: ejecutar el proceso de ingestión.
    ingestion_id = ingest_raw_exchange_rates(
        client=client,
        session_factory=session_factory,
        provider="ECB",
        base_currency="EUR",
        quote_currencies=["USD", "GBP"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    try:
        # Consultar de nuevo PostgreSQL con una sesión independiente.
        with session_factory() as session:
            ingestion = session.get(RawApiIngestion, ingestion_id)

            assert ingestion is not None
            assert ingestion.ingestion_id == ingestion_id
            assert ingestion.source_name == FRANKFURTER_SOURCE_NAME
            assert ingestion.provider == "ECB"

            assert ingestion.request_parameters == {
                "base": "EUR",
                "quotes": "USD,GBP",
                "from": "2026-01-01",
                "to": "2026-01-31",
            }

            assert ingestion.response_payload == raw_payload
            assert ingestion.payload_hash == calculate_payload_hash(raw_payload)
            assert ingestion.fetched_at is not None

    finally:
        with session_factory.begin() as session:
            ingestion_to_delete = session.get(
                RawApiIngestion,
                ingestion_id,
            )

            if ingestion_to_delete is not None:
                session.delete(ingestion_to_delete)

    # Comprobar que el cliente recibió los parámetros esperados.
    client.get_rates.assert_called_once_with(
        base_currency="EUR",
        quote_currencies=["USD", "GBP"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
