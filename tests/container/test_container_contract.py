"""Контракт сборки ЛР6: стадии Dockerfile и базовая конфигурация Compose (без Docker)."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")
COMPOSE_TEXT = (ROOT / "compose.yaml").read_text(encoding="utf-8")
COMPOSE = yaml.safe_load(COMPOSE_TEXT)


def stage(name: str) -> str:
    """Текст одной стадии Dockerfile: от FROM ... AS name до следующего FROM."""
    match = re.search(rf"^FROM .+ AS {name}$(.*?)(?=^FROM |\Z)", DOCKERFILE, re.M | re.S)
    assert match, f"нет стадии {name}"
    return match.group(1)


def test_python_is_pinned_312_slim():
    assert re.search(r"^ARG PYTHON_IMAGE=python:3\.12\.\d+-slim", DOCKERFILE, re.M)
    assert ":latest" not in DOCKERFILE and ":latest" not in COMPOSE_TEXT


def test_quality_stage_is_a_gate_before_runtime():
    quality = stage("quality")
    for command in (
        "python -m ruff check",
        "python -m pytest -q",
        "python -m housing_price.validate_data",
        "sha256sum --check",
        "python -m housing_price.train",
    ):
        assert command in quality, command
    # runtime берет модель и пакет только из quality: без успешных проверок их нет.
    assert "COPY --from=quality /build/models/model.joblib" in stage("runtime")
    assert "from=quality,source=/wheels" in stage("runtime")


def test_dependencies_installed_before_source_code():
    quality = stage("quality")
    assert quality.index('pip install ".[dev,tracking]"') < quality.index("COPY src")
    assert quality.index("python -m housing_price.train") < quality.index("COPY README.md")


def test_runtime_has_no_tests_data_or_dev_tools():
    runtime = stage("runtime")
    assert "COPY tests" not in runtime and "COPY data" not in runtime
    assert "[dev" not in runtime and "tracking" not in runtime


def test_runtime_runs_as_non_root_with_readiness_healthcheck():
    runtime = stage("runtime")
    assert "USER 10001:10001" in runtime
    assert re.search(r"HEALTHCHECK .*\n.*CMD \[.*/readyz", runtime)
    assert "curl" not in runtime
    assert re.search(r'^CMD \["uvicorn", "housing_price\.api:app"', runtime, re.M)


def test_compose_has_no_version_and_requires_commit_tag():
    assert "version" not in COMPOSE
    app = COMPOSE["services"]["app"]
    assert app["image"].startswith("mlops-housing-price:${IMAGE_TAG:?")
    assert app["build"]["target"] == "runtime"
    assert "${APP_PORT:-8080}:8080" in app["ports"][0]


def test_compose_healthcheck_uses_readyz():
    test = " ".join(COMPOSE["services"]["app"]["healthcheck"]["test"])
    assert "/readyz" in test
