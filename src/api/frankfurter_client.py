from collections.abc import Sequence
from datetime import date

import httpx
from pydantic import TypeAdapter

from financial_pipeline.api.schemas import FrankfurterRateResponse
from financial_pipeline.config import Settings

rate_list_adapter = TypeAdapter(list[FrankfurterRateResponse])

class FrankfurterClient:
    def __init__(
            self,
            http_client: httpx.Client,
            settings: Settings,
    ) -> None:
        self._http_client = http_client
        self._settings = settings

    def get_rates(
        self, *, base_currency: str,
        quote_currencies: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> list[FrankfurterRateResponse]:
        response = self._http_client.get(
            slef._settings.frankfurter_api_urls,
            params={
                "base": base_currency,
                "quotes": ",".join(quote_currencies),
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
        )
        response.raise_for_status()

        return rate_list_adpater.validate_python(response.json())