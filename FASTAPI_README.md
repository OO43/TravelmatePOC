# TravelMate Passenger API

This service connects passenger app inputs to the existing TravelMate PoC vocabulary.
The PoC evaluation and driver-alert logic remain unchanged.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_api.txt
uvicorn travelmate_api.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` for the generated API documentation.

## First end-to-end request

```bash
curl -X POST http://127.0.0.1:8000/api/v1/journey-sessions \
  -H 'Content-Type: application/json' \
  -d '{
    "passenger_id": "passenger-1",
    "journey_id": "journey-1",
    "vehicle_id": "bus-24",
    "declared_ui_options": ["extra_time_exiting"],
    "consent_to_support_sharing": true,
    "consent_enhanced_supervision": false,
    "stop_request": false
  }'
```

The default SQLite database is `travelmate_api.db`. Set `TRAVELMATE_API_DB` to
use another path. Authentication and PostgreSQL are intentionally the next phase;
the current endpoint accepts `passenger_id` only for PoC integration testing.

## Feed an active API session into the existing runtime

Run the API and the runtime with the same database path, then set the vehicle:

```bash
export TRAVELMATE_API_DB="$PWD/travelmate_api.db"
export TRAVELMATE_VEHICLE_ID="bus-24"
python runtime_loop.py
```

When both variables are present, `passenger_app_adapter.py` reads the newest
active session for that vehicle. With either variable absent, its existing fake
and room-test behaviour remains unchanged.

## Tests

```bash
python -m unittest test_travelmate_api.py
```

## Schema modules

```text
travelmate_api/
└── schemas/
    ├── __init__.py
    ├── passenger.py
    ├── support.py
    ├── consent.py
    ├── engine.py
    └── common.py
```

- `passenger.py`: journey-session request and response; `stop_request` remains a journey action.
- `support.py`: `PassengerSupportRequest`, containing the existing declared UI options.
- `consent.py`: `PassengerConsentRequest`, containing both existing consent flags.
- `engine.py`: existing `EngineInput` contract.
- `common.py`: health and error responses.
- `__init__.py`: public exports, so existing `from travelmate_api.schemas import ...` imports still work.

`JourneySessionCreate` composes the support and consent models using inheritance.
The POST body remains flat, as shown above; no mobile payload migration is required.
For a focused import, use `from travelmate_api.schemas.support import PassengerSupportRequest`.

This refactor retains the POC's supported option vocabulary and derives support
categories through its adapter. The broader example fields (`support_types`,
`requires_step_free_access`, guidance flags and notes) are not implemented in the
current engine contract and are not silently accepted or stored by this API.
SQLite, persistence and consent enforcement remain as before.
