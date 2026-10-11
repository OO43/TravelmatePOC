from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .errors import ApiError
from .repository import create_repository
from .schemas import (
    ErrorBody,
    HealthResponse,
    JourneySessionCreate,
    JourneySessionResponse,
)
from .service import JourneySessionService, with_engine_input


settings = get_settings()
repository = create_repository(settings)
service = JourneySessionService(repository)


@asynccontextmanager
async def lifespan(_: FastAPI):
    repository.initialize()
    try:
        yield
    finally:
        if hasattr(repository, "close"):
            repository.close()


app = FastAPI(
    title="TravelMate Passenger API",
    version="0.1.0",
    description="Passenger-to-PoC integration API for TravelMate.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(ApiError)
async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    body = ErrorBody(code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse()


@app.post(
    "/api/v1/journey-sessions",
    response_model=JourneySessionResponse,
    status_code=201,
    tags=["journeys"],
)
def create_journey_session(payload: JourneySessionCreate) -> dict:
    return with_engine_input(service.create(payload))


@app.get(
    "/api/v1/journey-sessions/{session_id}",
    response_model=JourneySessionResponse,
    tags=["journeys"],
)
def get_journey_session(session_id: str) -> dict:
    return with_engine_input(service.get(session_id))

