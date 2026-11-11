import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from financial_pipeline.db.session import create_session_factory

pytestmark = pytest.mark.integration


def test_session_factory_can_execute_query(engine: Engine) -> None:
    session_factory = create_session_factory(engine)

    with session_factory() as db_session:
        result = db_session.execute(text("SELECT 1"))

        assert result.scalar_one() == 1
