# Financial Exchange-Rate Pipeline

> **Status:** Learning project in active development. The first end-to-end
> version supports validated, idempotent ingestion and analytical metrics.

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

## Data source

The pipeline uses the [Frankfurter v2 API](https://frankfurter.dev/) with the
ECB provider. The default currency pairs are:

- EUR/USD
- EUR/GBP
- EUR/JPY

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
- Validate quote coverage for every date returned by the provider; the
  pipeline does not invent missing calendar dates for weekends or holidays.
- Store raw payloads and ingestion metadata for traceability.
- Normalize valid rates into typed relational records.
- Load data idempotently using a natural key such as:

  ```text
  (rate_date, base_currency, quote_currency, provider)
  ```

- Compute analytical metrics, including daily rate changes.
- Expose a repeatable command for one pipeline run.
- Record useful execution logs, including fetched and inserted rate counts.

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

## Project structure

```text
.
├── alembic/                    # Database migrations
├── docs/data-model.md           # Schemas, constraints, and mart contract
├── src/financial_pipeline/
│   ├── api/                     # Frankfurter client and API schemas
│   ├── db/                      # ORM models, repositories, and sessions
│   ├── domain/                  # Business-level validation rules
│   ├── pipeline/                # Ingestion orchestration
│   ├── config.py                # Environment-based settings
│   └── main.py                  # Command-line entry point
├── tests/unit/                  # Isolated tests without PostgreSQL
├── tests/integration/           # PostgreSQL-backed tests
├── compose.yaml
└── .env.example
```

See [the data model](docs/data-model.md) for the `raw`, `staging`, and `mart`
contracts.

## Local setup

### Prerequisites

- Python 3.12 or newer.
- [uv](https://docs.astral.sh/uv/).
- Docker Engine with Docker Compose.

### Configure the environment

Create a local configuration file and install the locked dependencies:

```bash
cp .env.example .env
uv sync
```

`.env` contains local PostgreSQL credentials. Keep it local and change the
example password before using this configuration outside local development.

### Start PostgreSQL

```bash
docker compose up -d
docker compose ps
```

The `postgres_data` Docker volume preserves local database data when the
container is recreated. Stop the service without deleting that volume with:

```bash
docker compose down
```

### Create and migrate the databases

Apply migrations to the development database:

```bash
uv run alembic upgrade head
```

Integration tests use a separate database named `financial_pipeline_test`.
Create it once after PostgreSQL is running:

```bash
docker compose exec postgres sh -c \
  'createdb -U "$POSTGRES_USER" financial_pipeline_test'
```

If PostgreSQL reports that the database already exists, continue with the next
command. Export the variables in `.env`, then apply the same migrations to the
test database:

```bash
set -a
source .env
set +a

FINANCIAL_PIPELINE_DATABASE_URL="$TEST_DATABASE_URL" \
  uv run alembic upgrade head
```

## Run the pipeline

Fetch rates for an inclusive date range:

```bash
uv run python -m financial_pipeline.main \
  --start-date 2026-01-15 \
  --end-date 2026-01-15
```

The command writes one traceable raw-ingestion row for each execution. The
staging natural key prevents duplicate exchange-rate rows on reruns with the
same rates.

Inspect the analytical mart with:

```bash
docker compose exec postgres sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -c \
  "SELECT * FROM mart.daily_exchange_rate_metrics ORDER BY rate_date, quote_currency;"'
```

## Tests and quality checks

The test database URL must be exported before running the complete test suite:

```bash
set -a
source .env
set +a

uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run alembic check
```

Run only unit tests without PostgreSQL with:

```bash
uv run pytest -m "not integration"
```

## Implemented milestones

1. Define the API contract, relational model, and architecture.
2. Initialize the Python package, dependencies, configuration, and tests.
3. Add PostgreSQL and Alembic migrations.
4. Implement extraction, validation, raw ingestion, and idempotent loading.
5. Add staging and mart transformations with quality checks.
6. Add logging, tests, documentation, and final review.

## Definition of done

The first project version is complete when a fresh local environment can start
PostgreSQL, apply migrations, execute the pipeline repeatedly without
duplicates, run the test suite and quality checks, and reproduce documented
analytical outputs.
