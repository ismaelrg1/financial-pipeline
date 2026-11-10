from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
from sqlalchemy import delete, select, func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from financial_pipeline.api.frankfurter_client import FrankfurterClient
from financial_pipeline.db.orm_models import RawApiIngestion, StagingExchangeRate
from financial_pipeline.db.session import create_session_factory
from financial_pipeline.pipeline.exchange_rates import (
    ExchangeRateIngestionResult,
    FRANKFURTER_SOURCE_NAME,
    calculate_payload_hash,
    ingest_exchange_rates,
)
from financial_pipeline.api.schemas import (
    FrankfurterRateResponse,
    FrankfurterRatesFetch,
)

pytestmark = pytest.mark.integration


def test_ingest_exchange_rates_persists_raw_and_staging(engine: Engine) -> None:
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
    result = ingest_exchange_rates(
        client=client,
        session_factory=session_factory,
        provider="ECB",
        base_currency="EUR",
        quote_currencies=["USD", "GBP"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    ingestion_id = result.ingestion_id

    try:
        # Controlar resultados pipeline
        assert ingestion_id is not None
        assert result.fetched_rate_count == 2
        assert result.inserted_rate_count == 2

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

            # Verificar staging exchange rates
            statement = (
                select(StagingExchangeRate)
                .where(
                    StagingExchangeRate.source_ingestion_id == ingestion_id
                )
                .order_by(StagingExchangeRate.quote_currency)
            )

            staging_rates = session.scalars(statement).all()

            assert len(staging_rates) == 2

            # GBP
            gbp_rate = staging_rates[0]

            assert gbp_rate.source_ingestion_id == ingestion_id
            assert gbp_rate.rate_date == date(2026, 1, 15)
            assert gbp_rate.base_currency == "EUR"
            assert gbp_rate.quote_currency == "GBP"
            assert gbp_rate.provider == "ECB"
            assert gbp_rate.rate == Decimal("0.8652")


            # USD
            usd_rate = staging_rates[1]

            assert usd_rate.source_ingestion_id == ingestion_id
            assert usd_rate.rate_date == date(2026, 1, 15)
            assert usd_rate.base_currency == "EUR"
            assert usd_rate.quote_currency == "USD"
            assert usd_rate.provider == "ECB"
            assert usd_rate.rate == Decimal("1.1625")

    finally:
        # Eliminar staging records antes de eliminar el raw ingestion
        with session_factory.begin() as session:
            session.execute(
                delete(StagingExchangeRate).where(
                    StagingExchangeRate.source_ingestion_id == ingestion_id
                )
            )

            session.execute(
                delete(RawApiIngestion).where(
                    RawApiIngestion.ingestion_id == ingestion_id
                )
            )

    # Comprobar que el cliente recibió los parámetros esperados.
    client.get_rates.assert_called_once_with(
        base_currency="EUR",
        quote_currencies=["USD", "GBP"],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )


def test_ingest_exchange_rates_keeps_staging_idempotent(
    engine: Engine,
) -> None:
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

    first_result: ExchangeRateIngestionResult | None = None
    second_result: ExchangeRateIngestionResult | None = None

    try:
        # First ingestion
        first_result = ingest_exchange_rates(
            client=client,
            session_factory=session_factory,
            provider="ECB",
            base_currency="EUR",
            quote_currencies=["USD", "GBP"],
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 15),
        )

        # Second ingestion with the same parameters and payload
        second_result = ingest_exchange_rates(
            client=client,
            session_factory=session_factory,
            provider="ECB",
            base_currency="EUR",
            quote_currencies=["USD", "GBP"],
            start_date=date(2026, 1, 15),
            end_date=date(2026, 1, 15),
        )

        # Verify ingestion results
        assert first_result.fetched_rate_count == 2
        assert first_result.inserted_rate_count == 2

        assert second_result.fetched_rate_count == 2
        assert second_result.inserted_rate_count == 0

        assert first_result.ingestion_id != second_result.ingestion_id

        assert client.get_rates.call_count == 2

        ingestion_ids = [
            first_result.ingestion_id,
            second_result.ingestion_id,
        ]

        with session_factory() as session:
            # Verify raw ingestions: one row per pipeline execution
            raw_ingestions = session.scalars(
                select(RawApiIngestion).where(
                    RawApiIngestion.ingestion_id.in_(ingestion_ids)
                )
            ).all()

            assert len(raw_ingestions) == 2

            raw_ingestion_ids = {
                ingestion.ingestion_id for ingestion in raw_ingestions
            }
            assert raw_ingestion_ids == set(ingestion_ids)

            # Verify staging: only the first execution inserted rates
            staging_rates = session.scalars(
                select(StagingExchangeRate)
                .where(
                    StagingExchangeRate.source_ingestion_id.in_(ingestion_ids)
                )
                .order_by(StagingExchangeRate.quote_currency)
            ).all()

            assert len(staging_rates) == 2

            gbp_rate, usd_rate = staging_rates

            assert gbp_rate.quote_currency == "GBP"
            assert gbp_rate.base_currency == "EUR"
            assert gbp_rate.rate_date == date(2026, 1, 15)
            assert gbp_rate.provider == "ECB"
            assert gbp_rate.rate == Decimal("0.8652")

            assert usd_rate.quote_currency == "USD"
            assert usd_rate.base_currency == "EUR"
            assert usd_rate.rate_date == date(2026, 1, 15)
            assert usd_rate.provider == "ECB"
            assert usd_rate.rate == Decimal("1.1625")

            # Both staging rows must reference the first ingestion
            assert {
                rate.source_ingestion_id for rate in staging_rates
            } == {first_result.ingestion_id}

            assert all(
                rate.source_ingestion_id != second_result.ingestion_id
                for rate in staging_rates
            )

    finally:
        ingestion_ids = [
            result.ingestion_id
            for result in (first_result, second_result)
            if result is not None
        ]

        if ingestion_ids:
            with session_factory.begin() as session:
                session.execute(
                    delete(StagingExchangeRate).where(
                        StagingExchangeRate.source_ingestion_id.in_(
                            ingestion_ids
                        )
                    )
                )

                session.execute(
                    delete(RawApiIngestion).where(
                        RawApiIngestion.ingestion_id.in_(ingestion_ids)
                    )
                )


def test_ingest_exchange_rates_rolls_back_raw_when_staging_insert_fails(
    engine: Engine,
) -> None:
    raw_payload = [
        {
            "date": "2026-02-15",
            "base": "EUR",
            "quote": "EUR",
            "rate": 1.0,
        },
    ]

    invalid_rate = FrankfurterRateResponse.model_construct(
        date=date(2026, 2, 15),
        base="EUR",
        quote="EUR",
        rate=Decimal("1.0"),
    )

    fetched_rates = FrankfurterRatesFetch(
        raw_payload=raw_payload,
        rates=[invalid_rate],
    )

    payload_hash = calculate_payload_hash(raw_payload)

    client = Mock(spec=FrankfurterClient)
    client.get_rates.return_value = fetched_rates

    session_factory = create_session_factory(engine)

    with pytest.raises(IntegrityError):
        ingest_exchange_rates(
            client=client,
            session_factory=session_factory,
            provider="ECB",
            base_currency="EUR",
            quote_currencies=["EUR"],
            start_date=date(2026, 2, 15),
            end_date=date(2026, 2, 15),
        )

    client.get_rates.assert_called_once()

    # Verify that the raw ingestion was rolled back as well.
    with session_factory() as session:
        raw_ingestion_count = session.scalar(
            select(func.count())
            .select_from(RawApiIngestion)
            .where(RawApiIngestion.payload_hash == payload_hash)
        )

    assert raw_ingestion_count == 0
