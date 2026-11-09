from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

# patron moneda "EUR" "USD"..
CurrencyCode = Annotated[
    str,
    Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"),
]


class FrankfurterRateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    date: date
    base: CurrencyCode
    quote: CurrencyCode
    rate: Decimal = Field(gt=0)

    @field_validator("base", "quote", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        """Normalize currency text before Literal validation."""
        if isinstance(value, str):
            return value.strip().upper()
        return value
