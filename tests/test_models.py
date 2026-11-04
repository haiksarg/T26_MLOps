"""Варианты ЛР4: параметры моделей и сохранение обученного pipeline через skops."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import skops.io as sio
import yaml
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from housing_price.models import MODEL_KINDS, SKOPS_TRUSTED_TYPES, make_estimator
from housing_price.train import train_and_evaluate

ROOT = Path(__file__).resolve().parents[1]
MODEL_CASES = [
    ("median_baseline", DummyRegressor),
    ("linear_regression", LinearRegression),
    ("random_forest", RandomForestRegressor),
]


@pytest.mark.parametrize(("kind", "expected_class"), MODEL_CASES)
def test_each_model_kind_builds_the_expected_estimator(kind, expected_class):
    estimator = make_estimator(kind, seed=13, params={"rf_n_estimators": 7, "rf_max_depth": 3})

    assert kind in MODEL_KINDS
    assert isinstance(estimator, expected_class)
    if kind == "median_baseline":
        assert estimator.strategy == "median"


def test_random_forest_uses_configured_parameters_and_seed():
    forest = make_estimator("random_forest", 13, {"rf_n_estimators": 7, "rf_max_depth": 3})

    assert forest.n_estimators == 7
    assert forest.max_depth == 3
    assert forest.random_state == 13
    assert forest.n_jobs == -1


@pytest.mark.parametrize("kind", [case[0] for case in MODEL_CASES])
def test_trained_pipeline_skops_round_trip_preserves_predictions(kind, tmp_path):
    params = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))
    # Маленький лес проверяет сериализацию быстро; качество оценивается на полном наборе.
    params["train"] = {
        "model": kind,
        "seed": 13,
        "rf_n_estimators": 7,
        "rf_max_depth": 3,
    }
    # Как в test_train: повторяем образец, чтобы в каждой категории хватило строк для split.
    frame = pd.concat([pd.read_csv(ROOT / "data" / "housing_sample.csv")] * 3, ignore_index=True)
    model, _, example = train_and_evaluate(frame, params)
    expected = model.predict(example)

    serialized = sio.dumps(model)
    untrusted = sio.get_untrusted_types(data=serialized)
    assert set(untrusted) <= set(SKOPS_TRUSTED_TYPES[kind])

    path = tmp_path / f"{kind}.skops"
    path.write_bytes(serialized)
    loaded = sio.load(path, trusted=SKOPS_TRUSTED_TYPES[kind])
    actual = loaded.predict(example)

    assert actual.shape == (len(example),)
    assert np.isfinite(actual).all()
    # Параллельное суммирование деревьев допускает погрешность округления float.
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-9)
