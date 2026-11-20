"""HTTP API модели (ЛР6): /healthz, /readyz, /predict.

    MODEL_PATH=models/model.joblib uvicorn housing_price.api:app --port 8080

/healthz — процесс отвечает. /readyz — bundle модели загружен и прошел проверку формата;
по нему работает healthcheck контейнера. /predict — прогноз median_house_value для одного района.
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from housing_price.train import BundleError, load_bundle

LOGGER = logging.getLogger("uvicorn.error")
DEFAULT_MODEL_PATH = "models/model.joblib"
NOT_READY = "модель не загружена"


class HousingFeatures(BaseModel):
    """Признаки одного района (block group). Границы — из data/contract.json."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "longitude": -122.23,
                    "latitude": 37.88,
                    "housing_median_age": 41,
                    "total_rooms": 880,
                    "total_bedrooms": 129,
                    "population": 322,
                    "households": 126,
                    "median_income": 8.3252,
                    "ocean_proximity": "NEAR BAY",
                }
            ]
        },
    )

    longitude: float = Field(ge=-124.5, le=-114.0)
    latitude: float = Field(ge=32.5, le=42.0)
    housing_median_age: int = Field(ge=0, le=52)
    total_rooms: int = Field(ge=1)
    total_bedrooms: int | None = Field(ge=0)
    population: int = Field(ge=1)
    households: int = Field(ge=1)
    median_income: float = Field(ge=0, le=15.0001)
    ocean_proximity: Literal["<1H OCEAN", "INLAND", "ISLAND", "NEAR BAY", "NEAR OCEAN"]


class PredictionResponse(BaseModel):
    predicted_value: float
    model_version: str
    request_id: str


class StatusResponse(BaseModel):
    status: str
    model_version: str | None = None


def model_version(bundle: dict[str, Any]) -> str:
    """Версия модели из bundle: вариант, seed и начало SHA-256 данных обучения."""
    train = bundle["train"]
    return f"{train['model']}-seed{train['seed']}-data{bundle['data']['data_sha256'][:8]}"


def create_app(model_path: Path | None = None) -> FastAPI:
    path = model_path or Path(os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH))

    @asynccontextmanager
    async def lifespan(api: FastAPI):
        api.state.bundle = None
        api.state.model_version = None
        try:
            bundle = load_bundle(path)
        except (FileNotFoundError, BundleError) as exc:
            LOGGER.warning("модель не готова: %s", exc)
        else:
            api.state.bundle = bundle
            api.state.model_version = os.getenv("MODEL_VERSION") or model_version(bundle)
            LOGGER.info("модель загружена: %s (%s)", path, api.state.model_version)
        yield

    api = FastAPI(
        title="Housing Price API",
        version="0.1.0",
        description="Учебный API прогноза медианной стоимости жилья в районе (California Housing).",
        lifespan=lifespan,
    )

    @api.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "")
        if not request_id or len(request_id) > 128:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @api.get("/healthz", response_model=StatusResponse, tags=["service"])
    def health() -> StatusResponse:
        return StatusResponse(status="ok")

    @api.get("/readyz", response_model=StatusResponse, tags=["service"])
    def ready() -> StatusResponse:
        if api.state.bundle is None:
            raise HTTPException(status_code=503, detail=NOT_READY)
        return StatusResponse(status="ready", model_version=api.state.model_version)

    @api.post("/predict", response_model=PredictionResponse, tags=["prediction"])
    def predict(features: HousingFeatures, request: Request) -> PredictionResponse:
        bundle = api.state.bundle
        if bundle is None:
            raise HTTPException(status_code=503, detail=NOT_READY)
        frame = pd.DataFrame([features.model_dump()])[bundle["features"]]
        value = float(bundle["model"].predict(frame)[0])
        return PredictionResponse(
            predicted_value=value,
            model_version=api.state.model_version,
            request_id=request.state.request_id,
        )

    return api


app = create_app()
