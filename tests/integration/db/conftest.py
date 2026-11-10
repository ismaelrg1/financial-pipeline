import pytest
from sqlalchemy.orm import Session

from financial_pipeline.db.orm_models import RawApiIngestion
from factories import build_raw_api_ingestion


@pytest.fixture
def persisted_raw_ingestion(
    db_session: Session,
) -> RawApiIngestion:
    ingestion = build_raw_api_ingestion()

    db_session.add(ingestion)
    db_session.flush()

    return ingestion