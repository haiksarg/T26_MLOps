"""HTTP API (ЛР6): ответы /healthz, /readyz и /predict при загруженной модели."""

import math

import pytest
from fastapi.testclient import TestClient

from housing_price.api import HousingFeatures, create_app
from housing_price.features import FEATURES

EXAMPLE = HousingFeatures.model_config["json_schema_extra"]["examples"][0]


@pytest.fixture
def client(bundle_path):
    with TestClient(create_app(bundle_path)) as test_client:
        yield test_client


def test_request_schema_covers_exactly_model_features():
    assert set(HousingFeatures.model_fields) == set(FEATURES)


def test_healthz_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_reports_loaded_model(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["model_version"] == "random_forest-seed42-data00000000"


def test_predict_returns_finite_positive_value(client):
    response = client.post("/predict", json=EXAMPLE)
    assert response.status_code == 200
    body = response.json()
    assert math.isfinite(body["predicted_value"]) and body["predicted_value"] > 0
    assert body["model_version"]
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_predict_keeps_client_request_id(client):
    response = client.post("/predict", json=EXAMPLE, headers={"X-Request-ID": "lr6-check"})
    assert response.json()["request_id"] == "lr6-check"


def test_predict_accepts_missing_total_bedrooms(client):
    response = client.post("/predict", json={**EXAMPLE, "total_bedrooms": None})
    assert response.status_code == 200


def test_model_version_can_be_overridden(bundle_path, monkeypatch):
    monkeypatch.setenv("MODEL_VERSION", "rf-release-candidate")
    with TestClient(create_app(bundle_path)) as test_client:
        assert test_client.get("/readyz").json()["model_version"] == "rf-release-candidate"


@pytest.mark.parametrize(
    "change",
    [
        {"ocean_proximity": "ON THE MOON"},
        {"latitude": 50.0},
        {"housing_median_age": 53},
        {"median_house_value": 100000},
    ],
    ids=["unknown-category", "out-of-state", "above-top-coding", "target-in-request"],
)
def test_predict_rejects_request_outside_contract(client, change):
    response = client.post("/predict", json={**EXAMPLE, **change})
    assert response.status_code == 422
