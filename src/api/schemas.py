from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

CurrencyCode = Annotated[
    str,
    Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"),
]


class FrankfurterRateResponse(BaseModel):
    date: date
    base: CurrencyCode
    quote: CurrencyCode
    rate: Decimal | None

    @field_validator("base", "quote", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        """Normalize currency text before Literal validation."""
        if isinstance(value, str):
            return value.strip().upper()
        return value
