from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from financial_pipeline.db.base import Base


class RawApiIngestion(Base):
    __tablename__ = "api_ingestions"
    __table_args__ = (
        CheckConstraint(
            "payload_hash ~ '^[0-9a-f]{64}$'",
            name="chk_api_ingestions_payload_hash_format",
        ),
        {"schema": "raw"},
    )

    ingestion_id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )

    source_name: Mapped[str] = mapped_column(String(50), nullable=False)

    provider: Mapped[str] = mapped_column(String(50), nullable=False)

    request_parameters: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False)

    response_payload: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, nullable=False
    )

    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # relationship
    exchange_rates: Mapped[list["StagingExchangeRate"]] = relationship(
        back_populates="source_ingestion",
    )


class StagingExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (
        CheckConstraint(
            "base_currency ~'^[A-Z]{3}$'",
            name="chk_exchange_rates_base_currency_format",
        ),
        CheckConstraint(
            "quote_currency ~'^[A-Z]{3}$'",
            name="chk_exchange_rates_quote_currency_format",
        ),
        CheckConstraint(
            "base_currency <> quote_currency",
            name="chk_exchange_rates_different_currencies",
        ),
        CheckConstraint(
            "rate > 0",
            name="chk_exchange_rates_positive_rate",
        ),
        UniqueConstraint(
            "rate_date",
            "base_currency",
            "quote_currency",
            "provider",
            name="uq_exchange_rates_rate_date_base_quote_provider",
        ),
        {"schema": "staging"},
    )

    exchange_rate_id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )

    source_ingestion_id: Mapped[int] = mapped_column(
        ForeignKey("raw.api_ingestions.ingestion_id"), nullable=False
    )

    rate_date: Mapped[date] = mapped_column(
        Date(),
        nullable=False,
    )

    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)

    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)

    provider: Mapped[str] = mapped_column(String(50), nullable=False)

    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # relationship
    source_ingestion: Mapped["RawApiIngestion"] = relationship(
        back_populates="exchange_rates",
    )
