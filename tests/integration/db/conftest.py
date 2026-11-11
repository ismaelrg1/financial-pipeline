from collections.abc import Callable

import pytest
from factories import build_raw_api_ingestion
from sqlalchemy.orm import Session

from financial_pipeline.db.orm_models import RawApiIngestion


@pytest.fixture
def persisted_raw_ingestion(
    db_session: Session,
) -> RawApiIngestion:
    ingestion = build_raw_api_ingestion()

    db_session.add(ingestion)
    db_session.flush()

    return ingestion


@pytest.fixture
def raw_ingestion_factory(
    db_session: Session,
) -> Callable[..., RawApiIngestion]:
    def create(
        *,
        payload_hash: str = "b" * 64,
    ) -> RawApiIngestion:
        ingestion = build_raw_api_ingestion(
            payload_hash=payload_hash,
        )

        db_session.add(ingestion)
        db_session.flush()

        return ingestion

    return create
