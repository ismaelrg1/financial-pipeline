from collections.abc import Generator
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from financial_pipeline.db.orm_models import RawApiIngestion
from factories import build_raw_api_ingestion


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    database_url = os.environ.get("TEST_DATABASE_URL")

    if database_url is None:
        pytest.fail("TEST_DATABASE_URL environment variable is required")

    test_engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    yield test_engine

    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def persisted_raw_ingestion(
    db_session: Session,
) -> RawApiIngestion:
    ingestion = build_raw_api_ingestion()

    db_session.add(ingestion)
    db_session.flush()

    return ingestion