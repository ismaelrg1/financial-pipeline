# Financial Exchange-Rate Pipeline

> **Status:** In progress. API validation, PostgreSQL infrastructure,
> Alembic migrations, ORM models, and integration tests are implemented.

## Objective

Build a reproducible batch data pipeline that ingests foreign-exchange rates
from a public API, validates the external payload, stores raw and normalized
data in PostgreSQL, and exposes analytical metrics.

The project is the Phase 1 integrated implementation for Python, SQL,
PostgreSQL, Docker Compose, configuration, testing, and data-engineering
fundamentals.

## Problem statement

Financial applications and analytical reports need reliable historical
exchange-rate data. The pipeline must collect daily rates for selected
currency pairs, preserve the original API response for traceability, validate
and normalize the records, and make them available for analysis without
creating duplicate records when it is rerun.

## Proposed source

The initial source will be the [Frankfurter v2 API](https://frankfurter.dev/),
using a documented provider such as ECB. The first currency pairs are:

- EUR/USD
- EUR/GBP
- EUR/JPY

The exact request parameters and response contract will be verified before
implementation.

## Intended data flow

```text
Frankfurter API
      |
      v
Python extractor and Pydantic validation
      |
      v
Domain quality validation
      |
      v
PostgreSQL raw layer       -- original payload and ingestion metadata
      |
      v
PostgreSQL staging layer   -- typed and normalized exchange rates
      |
      v
PostgreSQL mart layer      -- daily rates and rate-change metrics
```

## Functional requirements

- Extract historical and recent exchange rates for the selected pairs.
- Validate external API payloads at the ingestion boundary with Pydantic v2.
- Reject empty responses, unexpected base or quote currencies, duplicate
  `(date, base_currency, quote_currency)` keys, and incomplete requested
  quote coverage before persisting data.
- Store raw payloads and ingestion metadata for traceability.
- Normalize valid rates into typed relational records.
- Load data idempotently using a natural key such as:

  ```text
  (rate_date, base_currency, quote_currency, provider)
  ```

- Compute analytical metrics, including daily rate changes.
- Expose a repeatable command for one pipeline run.
- Record useful logs and quality metrics for every execution.

## Engineering requirements

- Python 3.12 and `uv` with a project-local virtual environment.
- SQLAlchemy ORM and Alembic migrations.
- PostgreSQL started through this project's Docker Compose configuration.
- Environment-based configuration with safe defaults in `.env.example`.
- No secrets, local `.env` files, virtual environments, logs, database files,
  or generated outputs committed to version control.
- Unit tests for pure transformations and validation.
- Integration tests for PostgreSQL persistence and idempotency.
- Ruff, static type checking, and pytest run before completion.

## Scope boundaries

This is a batch pipeline. Airflow, dbt, Spark, Kafka, and production cloud
deployment are deliberately out of scope for the first version. Scheduling is
also external to the pipeline: the initial implementation will be run manually
and made idempotent before evaluating a local scheduler.

## Planned milestones

1. Define the API contract, relational model, and architecture.
2. Initialize the Python package, dependencies, configuration, and tests.
3. Add PostgreSQL and Alembic migrations.
4. Implement extraction, validation, raw ingestion, and idempotent loading.
5. Add staging and mart transformations with quality checks.
6. Add logging, tests, documentation, and final review.

## Definition of done

The project is complete when a fresh local environment can start PostgreSQL,
apply migrations, execute the pipeline repeatedly without duplicates, run the
test suite and quality checks, and reproduce documented analytical outputs.
