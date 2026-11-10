"""create exchange rate metrics mart

Revision ID: 9382b8f05c04
Revises: 12b5227a214e
Create Date: 2026-11-10 20:43:47.246868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9382b8f05c04'
down_revision: Union[str, Sequence[str], None] = '12b5227a214e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the exchange-rate analytical mart."""
    op.execute("CREATE SCHEMA IF NOT EXISTS mart")

    op.execute(
        """
        CREATE VIEW mart.daily_exchange_rate_metrics AS
        WITH rates_with_previous AS (
            SELECT
                rate_date,
                base_currency,
                quote_currency,
                provider,
                rate,
                LAG(rate) OVER (
                    PARTITION BY
                        base_currency,
                        quote_currency,
                        provider
                    ORDER BY rate_date
                ) AS previous_rate
            FROM staging.exchange_rates
        )
        SELECT
            rate_date,
            base_currency,
            quote_currency,
            provider,
            rate,
            previous_rate,
            rate - previous_rate AS absolute_change,
            CASE
                WHEN previous_rate IS NOT NULL
                    AND previous_rate <> 0
                THEN ((rate - previous_rate) / previous_rate) * 100
                ELSE NULL
            END AS percentage_change
        FROM rates_with_previous
        """
    )


def downgrade() -> None:
    """Drop the exchange-rate analytical mart."""
    op.execute("DROP VIEW IF EXISTS mart.daily_exchange_rate_metrics")
    op.execute("DROP SCHEMA IF EXISTS mart")
