# Event Router Service

Small FastAPI service that ingests lifecycle events, applies configurable messaging rules, deduplicates sends, and exposes an audit endpoint for Growth/CX.

## Functional Requirements

- Accept inbound events via HTTP (`POST /events`) with a strict request schema.
- Apply declarative rules from YAML (`src/configs/rules.yaml`).
- Suppress duplicates (`once_ever`, `once_per_day`) in UTC.
- Produce outbound send intents (email/sms/internal alert) via notifier stubs.
- Expose user audit trail (`GET /audit/{user_id}`) with recent events and sent/suppressed decisions.

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

## Run Locally (Docker Compose)

```bash
docker compose up --build
```

Service: `http://localhost:8000`

## API Documentation

After the app is running, open:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Run Locally (without Docker)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
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
