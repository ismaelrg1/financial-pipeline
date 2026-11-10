from collections.abc import Sequence
from datetime import date

import httpx
from pydantic import TypeAdapter

from financial_pipeline.api.schemas import FrankfurterRateResponse, FrankfurterRatesFetch
from financial_pipeline.config import Settings


raw_payload_adapter = TypeAdapter(list[dict[str, object]])
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
        self, 
        *, 
        base_currency: str,
        quote_currencies: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> FrankfurterRatesFetch:

        url = (
            f"{self._settings.frankfurter_api_base_url}"
            f"/providers/{self._settings.frankfurter_provider}/rates"
        )
        
        response = self._http_client.get(
            url,
            params={
                "base": base_currency,
                "quotes": ",".join(quote_currencies),
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
        )
        response.raise_for_status()

        raw_payload = raw_payload_adapter.validate_python(
            response.json(),
        )

        rates = rate_list_adapter.validate_python(raw_payload)

        return FrankfurterRatesFetch(
            raw_payload=raw_payload,
            rates=rates,
        )
