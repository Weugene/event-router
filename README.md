# Event Router Service

Small FastAPI service that ingests lifecycle events, applies configurable messaging rules, deduplicates sends, and exposes an audit endpoint for Growth/CX.

## Functional Requirements

### A. Accept inbound events

- Ingest JSON events via `POST /events` with validated schema.
- Supported `event_type` values:
  - `signup_completed`
  - `link_bank_success`
  - `payment_initiated`
  - `payment_failed`

### B. Apply messaging rules (declarative)

- Rules are declarative/configurable in `src/configs/rules.yaml` (not hardcoded branching logic).
- Implemented rule set:
  - If `signup_completed` and `user_traits.marketing_opt_in == true`, send `WELCOME_EMAIL`.
  - If `link_bank_success` occurs within 24h of `signup_completed`, send `BANK_LINK_NUDGE_SMS`.
  - If `payment_failed` and `properties.failure_reason == "INSUFFICIENT_FUNDS"`, send `INSUFFICIENT_FUNDS_EMAIL` once per user per calendar day.
  - If `payment_failed` and `properties.attempt_number >= 3`, send internal-only `HIGH_RISK_ALERT`.

### C. De-duplication / suppression

- Suppression policies supported:
  - `once_ever` (e.g., `WELCOME_EMAIL`)
  - `once_per_day` in UTC (e.g., `INSUFFICIENT_FUNDS_EMAIL`, `HIGH_RISK_ALERT`)
- Duplicate sends are recorded as `suppressed` with a reason in audit data.

### D. Produce outbound send request

- Instead of calling a real provider, notifier stubs record intended sends with:
  - `user_id`
  - `template_name`
  - `channel` (`email`, `sms`, `internal_alert`)
  - `timestamp`
  - `reason` (short explanation for why the message was sent)

### E. Expose audit/debug endpoint

- `GET /audit/{user_id}` returns:
  - recent events seen for the user
  - message decisions that were `sent` or `suppressed`
  - suppression explanation (for example, already sent in current UTC day)

## Non-functional Requirements

- Python 3.12
- FastAPI + Uvicorn
- Postgres + asyncpg
- Docker Compose for local run
- Ruff + pre-commit hooks

## Project Structure

```text
src/
  endpoints/
    events.py
    audit.py
  settings/
    build_logger.py
    configuration_singleton.py
  clients/
    asyncpg_client.py
    pg_store.py
    sms_notifier.py
    email_notifier.py
  middleware/
    context_logger_middleware.py
    tracer.py
    timeout.py
  configs/
    emails_templates.yaml
    rules.yaml
  main.py
```

## Run Everything with Docker Compose

```bash
# Development (app + postgres, auto-reload, single worker)
docker compose --profile dev up --build

# Production-like (app + postgres, multiple workers, no reload)
docker compose --profile prod up --build
```

Service: `http://localhost:8000`

Stop and clean up:

```bash
docker compose --profile dev down
# or
docker compose --profile prod down

# Remove containers + network + Postgres volume (deletes DB data)
docker compose --profile dev down -v
# or
docker compose --profile prod down -v
```

## API Documentation

After the app is running, open:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Run Locally (without Docker)

This mode requires an external PostgreSQL instance (for example, `docker compose up -d postgres`)
and matching DB env values (for host run use `POSTGRES_HOST=localhost`).

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv --python 3.12
source .venv/bin/activate

# Sync dependencies (including dev tools)
uv sync --dev

# Run API
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Alternative with pip:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run Tests

```bash
# Recommended: run tests in uv-managed environment
uv run pytest tests

# Alternative if using a local venv
pytest tests
```

## Example: POST Event

```bash
curl -X POST "http://localhost:8000/events" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u_12345",
    "event_type": "payment_failed",
    "event_timestamp": "2025-10-31T19:22:11Z",
    "properties": {
      "amount": 1425.00,
      "attempt_number": 2,
      "failure_reason": "INSUFFICIENT_FUNDS"
    },
    "user_traits": {
      "email": "maria@example.com",
      "country": "PT",
      "marketing_opt_in": true,
      "risk_segment": "MEDIUM"
    }
  }'
```

## Example: GET Audit

```bash
curl "http://localhost:8000/audit/u_12345"
```

## Assumptions

- Only one `signup_completed` event exists per user (guaranteed).
- `HIGH_RISK_ALERT` is deduplicated via `once_ever`.
- UTC is the source of truth for suppression windows.
- Audit stores only message decisions that were `sent` or `suppressed`.
