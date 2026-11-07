"""Предусловия метрик и отказ обучения при неопределенном mae_skill."""

import math
from functools import partial

import pytest

from housing_price.features import TARGET
from housing_price.metrics import evaluate_regression, mae, rmse
from housing_price.train import train_and_evaluate

METRICS = [
    mae,
    rmse,
    pytest.param(partial(evaluate_regression, reference=1.0), id="evaluate_regression"),
]


@pytest.mark.parametrize("metric", METRICS)
@pytest.mark.parametrize(
    ("y_true", "y_pred", "message"),
    [
        pytest.param([1.0, 2.0], [1.0], "Разная длина", id="length-mismatch"),
        pytest.param([], [], "Пустые", id="empty"),
    ],
)
def test_metrics_reject_invalid_lengths(metric, y_true, y_pred, message):
    with pytest.raises(ValueError, match=message):
        metric(y_true, y_pred)


@pytest.mark.parametrize("metric", METRICS)
@pytest.mark.parametrize("position", [0, 1], ids=["y_true", "y_pred"])
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf], ids=["nan", "inf", "-inf"])
def test_metrics_reject_nonfinite_values(metric, position, value):
    y_true, y_pred = [1.0, 2.0], [1.0, 2.0]
    (y_true, y_pred)[position][1] = value

    with pytest.raises(ValueError, match="конечные значения"):
        metric(y_true, y_pred)


@pytest.mark.parametrize("reference", [math.nan, math.inf, -math.inf])
def test_evaluate_regression_rejects_nonfinite_reference(reference):
    with pytest.raises(ValueError, match="reference.*конечное значение"):
        evaluate_regression([1.0, 3.0], [2.0, 2.0], reference)


@pytest.mark.parametrize("y_pred", [[5.0, 5.0], [4.0, 6.0]], ids=["perfect", "imperfect"])
def test_evaluate_regression_rejects_constant_target(y_pred):
    with pytest.raises(ValueError, match="baseline_mae.*0.*mae_skill"):
        evaluate_regression([5.0, 5.0], y_pred, reference=5.0)


@pytest.mark.parametrize(
    ("y_true", "y_pred", "reference", "expected"),
    [
        pytest.param(
            [0.0, 2.0], [0.0, 2.0], 1.0,
            {"mae": 0.0, "rmse": 0.0, "baseline_mae": 1.0, "mae_skill": 1.0},
            id="perfect",
        ),
        pytest.param(
            [0.0, 2.0], [1.0, 1.0], 1.0,
            {"mae": 1.0, "rmse": 1.0, "baseline_mae": 1.0, "mae_skill": 0.0},
            id="baseline",
        ),
        pytest.param(
            [0.0, 2.0], [4.0, 4.0], 1.0,
            {"mae": 3.0, "rmse": math.sqrt(10.0), "baseline_mae": 1.0, "mae_skill": -2.0},
            id="worse-than-baseline",
        ),
    ],
)
def test_evaluate_regression_returns_expected_metrics(y_true, y_pred, reference, expected):
    metrics = evaluate_regression(y_true, y_pred, reference)

    assert set(metrics) == {"mae", "rmse", "baseline_mae", "mae_skill"}
    assert metrics == pytest.approx(expected)
    assert metrics["mae"] >= 0
    assert metrics["rmse"] >= metrics["mae"]


def test_train_rejects_constant_target(pipeline_frame, params):
    pipeline_frame[TARGET] = 1000.0

    with pytest.raises(ValueError, match="baseline_mae.*0.*mae_skill"):
        train_and_evaluate(pipeline_frame, params)
