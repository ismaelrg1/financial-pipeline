# Data model

## raw.api_ingestions

Stores one raw record per external API request.

- `ingestion_id`: `BIGINT`, primary key, generated identity
- `source_name`: `VARCHAR(50) NOT NULL`
- `provider`: `VARCHAR(50) NOT NULL`
- `request_parameters`: `JSONB NOT NULL`
- `response_payload`: `JSONB NOT NULL`
- `payload_hash`: `VARCHAR(64) NOT NULL`
- `fetched_at`: `TIMESTAMPTZ NOT NULL`, defaults to `CURRENT_TIMESTAMP`

Constraints:

- `payload_hash` must be a 64-character lowercase hexadecimal value, intended to store a SHA-256 payload hash:
  `^[0-9a-f]{64}$`

## staging.exchange_rates

Stores one normalized exchange rate extracted from a raw ingestion.

- `exchange_rate_id`: `BIGINT`, primary key, generated identity
- `source_ingestion_id`: `BIGINT NOT NULL`, foreign key to `raw.api_ingestions`
- `rate_date`: `DATE NOT NULL`
- `base_currency`: `VARCHAR(3) NOT NULL`
- `quote_currency`: `VARCHAR(3) NOT NULL`
- `provider`: `VARCHAR(50) NOT NULL`
- `rate`: `NUMERIC(18, 8) NOT NULL`
- `ingested_at`: `TIMESTAMPTZ NOT NULL`, defaults to `CURRENT_TIMESTAMP`

Constraints:

- Currency codes must match `^[A-Z]{3}$`.
- Base and quote currencies must differ.
- `rate` must be greater than zero.
- `(rate_date, base_currency, quote_currency, provider)` is unique.
- Every exchange rate must reference an existing raw ingestion.

## mart.daily_exchange_rate_metrics

Read-only analytical view derived from `staging.exchange_rates`.

- `rate_date`: date of the observed rate
- `base_currency`
- `quote_currency`
- `provider`
- `rate`
- `previous_rate`: previous available rate in the same currency/provider series
- `absolute_change`: `rate - previous_rate`
- `percentage_change`: percentage variation from `previous_rate`

The first observed rate in each series has `NULL` change metrics.
