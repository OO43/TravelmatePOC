# Local PostgreSQL integration

The mobile API contract is unchanged. DATABASE_URL selects PostgreSQL;
without it the existing TRAVELMATE_API_DB SQLite repository remains available.
This migration creates an empty PostgreSQL database schema. It does not copy
old SQLite records or add passenger profiles/authentication.

## Setup on your Mac

Install and open Docker Desktop first. From the backend repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements_api.txt
cp .env.example .env
docker compose up -d --wait postgres
python -m alembic upgrade head
python -m uvicorn travelmate_api.main:app --host 0.0.0.0 --port 8000 --reload
```

If you already have a backend .env, merge the example's settings into it
instead of copying over it. The example password is only for local development.
The PostgreSQL port is bound to localhost and data is persisted in a named volume.
FastAPI and Alembic load the root .env without overriding exported environment values.
If port 5432 is occupied, change the Compose host port and DATABASE_URL together.

## Verify persistence

Confirm a journey in the mobile app. Expect POST 201 and GET 200.
In another backend terminal, inspect the saved record:

```bash
docker compose exec postgres psql -U travelmate -d travelmate -c \
  "SELECT session_id, passenger_id, vehicle_id, status, created_at FROM journey_sessions;"
```

Restart FastAPI and use the same session ID in GET /api/v1/journey-sessions/{session_id}.
The response should still contain the stored record. /health is a liveness endpoint;
it does not test database connectivity after startup.

The React Native .env continues to use your Mac's LAN address for EXPO_PUBLIC_API_URL.
Never put DATABASE_URL or database credentials in the mobile app.

## POC engine adapter

When running the engine independently, export DATABASE_URL and
TRAVELMATE_VEHICLE_ID=bus-24 in its terminal as well. The adapter selects PostgreSQL
when DATABASE_URL is set and SQLite when only TRAVELMATE_API_DB is configured.
The existing one-active-session-per-vehicle rule is preserved: confirming another
journey on that vehicle completes its previous session, even for another passenger.
PostgreSQL serializes concurrent confirmations for the same vehicle transactionally.
Multi-passenger behaviour is a separate product change.

## Tests and migrations

```bash
python -m unittest discover
python -m alembic current
```

For persistence and concurrent-confirmation integration tests, use an isolated
PostgreSQL database (never production):

```bash
TEST_DATABASE_URL="$DATABASE_URL" python -m unittest test_postgres_repository -v
```

This example requires DATABASE_URL exported in the shell, not just present in .env.
The tests apply migrations and delete only their own generated test-vehicle records.
Without TEST_DATABASE_URL these two tests are skipped.

Use Alembic migrations for PostgreSQL schema changes; the API never creates
PostgreSQL tables automatically. With the database configured, generate a future
migration using python -m alembic revision --autogenerate -m "describe change",
review it, then run python -m alembic upgrade head.

Existing SQLite data remains in its original file. To use it again, unset
DATABASE_URL (also remove/comment it in .env) and set TRAVELMATE_API_DB.
