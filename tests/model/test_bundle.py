"""Тесты bundle (ЛР5): состав файла модели, предсказание на одной строке, контроль загрузки.

Модель — регрессия, поэтому вместо ``predict_proba`` проверяется ``predict``: форма ``(1,)``
и конечное число (адаптация описана в docs/testing.md). Файлы создаются только в ``tmp_path``.
"""

import copy
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pytest

from housing_price.features import FEATURES, TARGET
from housing_price.split_data import split
from housing_price.train import (
    BUNDLE_FORMAT_VERSION,
    BUNDLE_KEYS,
    BundleError,
    build_bundle,
    load_bundle,
    train_and_evaluate,
)

MODEL_KINDS = ["median_baseline", "linear_regression", "random_forest"]
METRIC_NAMES = ["mae", "rmse", "baseline_mae", "mae_skill", "train_rows", "test_rows"]
VERSIONS = {"data_sha256": "ab" * 32, "contract_version": "1.0.0"}
# Порядок признаков закреплен независимо от features.py: модель обучена на этих столбцах.
PINNED_FEATURES = [
    "longitude",
    "latitude",
    "housing_median_age",
    "total_rooms",
    "total_bedrooms",
    "population",
    "households",
    "median_income",
    "ocean_proximity",
]


def make_config(params: dict, kind: str, seed: int) -> dict:
    config = copy.deepcopy(params)
    config["train"] = {**params["train"], "model": kind, "seed": seed}
    return config


@pytest.fixture
def make_bundle(params, pipeline_frame) -> Callable[..., dict[str, Any]]:
    """Обучить маленькую модель на pipeline_frame и вернуть bundle (как в train.main)."""

    def build(kind: str = "random_forest", seed: int = 42) -> dict[str, Any]:
        config = make_config(params, kind, seed)
        model, metrics, _ = train_and_evaluate(pipeline_frame, config)
        return build_bundle(model, config, metrics, VERSIONS)

    return build


@pytest.fixture
def save(tmp_path) -> Callable[..., Path]:
    def write(bundle: Any, name: str = "model.joblib") -> Path:
        path = tmp_path / name
        joblib.dump(bundle, path)
        return path

    return write


# ---------- состав bundle ----------


@pytest.mark.parametrize("kind", MODEL_KINDS)
def test_bundle_contains_all_documented_fields(make_bundle, kind):
    bundle = make_bundle(kind)

    missing = [key for key in BUNDLE_KEYS if key not in bundle]

    assert missing == []


def test_documented_fields_are_the_expected_ones():
    assert set(BUNDLE_KEYS) == {
        "format_version",
        "model",
        "features",
        "target",
        "train",
        "split",
        "metrics",
        "data",
    }


def test_bundle_features_match_features_including_order(make_bundle):
    bundle = make_bundle()

    assert bundle["features"] == FEATURES
    assert bundle["features"] == PINNED_FEATURES
    assert bundle["target"] == TARGET
    assert TARGET not in bundle["features"]


def test_bundle_records_format_version_and_data_versions(make_bundle):
    bundle = make_bundle()

    assert bundle["format_version"] == BUNDLE_FORMAT_VERSION
    assert bundle["data"] == VERSIONS


def test_bundle_records_training_parameters(make_bundle, params):
    bundle = make_bundle("random_forest", seed=7)
    expected = make_config(params, "random_forest", 7)["train"]

    assert bundle["train"] == expected
    assert bundle["train"]["model"] == "random_forest"
    assert bundle["train"]["rf_n_estimators"] == 5
    assert bundle["train"]["rf_max_depth"] == 3


def test_bundle_records_split_sizes_and_settings(make_bundle, params, pipeline_frame):
    bundle = make_bundle()
    recorded = bundle["split"]

    assert recorded["test_size"] == params["split"]["test_size"]
    assert recorded["stratify_column"] == params["split"]["stratify_column"]
    assert recorded["train_rows"] + recorded["test_rows"] == len(pipeline_frame)
    assert recorded["train_rows"] == bundle["metrics"]["train_rows"]
    assert recorded["test_rows"] == bundle["metrics"]["test_rows"]
    assert recorded["test_rows"] > 0


def test_bundle_records_finite_metrics(make_bundle):
    metrics = make_bundle()["metrics"]

    assert set(METRIC_NAMES) <= set(metrics)
    assert all(math.isfinite(float(metrics[name])) for name in METRIC_NAMES)
    assert metrics["mae"] >= 0
    assert metrics["baseline_mae"] > 0


def test_bundle_survives_save_and_load(make_bundle, save):
    bundle = make_bundle()

    loaded = load_bundle(save(bundle))

    assert {key: loaded[key] for key in BUNDLE_KEYS if key != "model"} == {
        key: bundle[key] for key in BUNDLE_KEYS if key != "model"
    }


# ---------- predict на одной строке ----------


@pytest.mark.parametrize("kind", MODEL_KINDS)
def test_predict_on_single_row_has_shape_one_and_finite_value(
    make_bundle, save, pipeline_frame, kind
):
    loaded = load_bundle(save(make_bundle(kind)))
    row = pipeline_frame.loc[[0], loaded["features"]]

    prediction = loaded["model"].predict(row)

    assert prediction.shape == (1,)
    assert math.isfinite(float(prediction[0]))


def test_random_forest_prediction_stays_within_train_target_range(
    make_bundle, save, params, pipeline_frame
):
    seed = 42
    loaded = load_bundle(save(make_bundle("random_forest", seed)))
    train_part, _ = split(pipeline_frame, {**params["split"], "random_state": seed})
    low, high = train_part[TARGET].min(), train_part[TARGET].max()

    predictions = loaded["model"].predict(pipeline_frame[loaded["features"]])

    # Лес усредняет значения листьев, а они — средние цели из train, поэтому за диапазон не выходят.
    assert predictions.min() >= low
    assert predictions.max() <= high


def test_loaded_model_repeats_predictions_of_trained_model(make_bundle, save, pipeline_frame):
    bundle = make_bundle()
    frame = pipeline_frame[bundle["features"]]

    loaded = load_bundle(save(bundle))

    np.testing.assert_allclose(loaded["model"].predict(frame), bundle["model"].predict(frame))


# ---------- контролируемая загрузка ----------


def corrupted_file(path: Path, bundle: dict) -> None:
    path.write_bytes(b"this is not a joblib file")


def empty_file(path: Path, bundle: dict) -> None:
    path.write_bytes(b"")


def missing_file(path: Path, bundle: dict) -> None:
    """Файл не создается."""


def not_a_bundle(path: Path, bundle: dict) -> None:
    joblib.dump([1, 2, 3], path)


LOAD_FAILURES = [
    pytest.param(corrupted_file, "не удалось загрузить модель", id="corrupted-file"),
    pytest.param(empty_file, "не удалось загрузить модель", id="empty-file"),
    pytest.param(missing_file, "не удалось загрузить модель", id="missing-file"),
    pytest.param(not_a_bundle, "ожидался bundle-словарь", id="not-a-dict"),
]


@pytest.mark.parametrize(("break_file", "message"), LOAD_FAILURES)
def test_load_bundle_rejects_unusable_file(make_bundle, tmp_path, break_file, message):
    path = tmp_path / "model.joblib"
    break_file(path, make_bundle())

    with pytest.raises(BundleError, match=message):
        load_bundle(path)


@pytest.mark.parametrize("key", BUNDLE_KEYS)
def test_load_bundle_rejects_bundle_without_a_field(make_bundle, save, key):
    bundle = make_bundle()
    del bundle[key]

    with pytest.raises(BundleError, match=f"нет полей: {key}"):
        load_bundle(save(bundle))


@pytest.mark.parametrize("version", [0, BUNDLE_FORMAT_VERSION + 1, str(BUNDLE_FORMAT_VERSION)])
def test_load_bundle_rejects_foreign_format_version(make_bundle, save, version):
    bundle = make_bundle()
    bundle["format_version"] = version

    with pytest.raises(BundleError, match=f"формат {version}, ожидался {BUNDLE_FORMAT_VERSION}"):
        load_bundle(save(bundle))


# ---------- детерминированность и seed ----------


def test_same_seed_gives_same_metrics_and_predictions_for_random_forest(
    params, pipeline_frame
):
    config = make_config(params, "random_forest", 42)
    frame = pipeline_frame[FEATURES]

    first_model, first_metrics, example = train_and_evaluate(pipeline_frame, config)
    second_model, second_metrics, _ = train_and_evaluate(pipeline_frame, config)

    assert second_metrics == pytest.approx(first_metrics)
    np.testing.assert_allclose(second_model.predict(frame), first_model.predict(frame))
    np.testing.assert_allclose(second_model.predict(example), first_model.predict(example))


@pytest.mark.parametrize("seed", [7, 13])
def test_seed_is_recorded_in_split_and_train_sections(make_bundle, seed):
    bundle = make_bundle("random_forest", seed)

    assert bundle["split"]["seed"] == seed
    assert bundle["train"]["seed"] == seed


def test_different_seed_changes_the_result(params, pipeline_frame):
    _, first, _ = train_and_evaluate(pipeline_frame, make_config(params, "random_forest", 7))
    _, second, _ = train_and_evaluate(pipeline_frame, make_config(params, "random_forest", 13))

    # Если seed игнорируется, оба запуска совпадут и сравнение по seed в ЛР4 теряет смысл.
    assert first["mae"] != pytest.approx(second["mae"])
