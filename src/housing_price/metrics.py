"""Метрики качества регрессионной модели цены жилья."""

import math
from collections.abc import Sequence


def _check_inputs(y_true: Sequence[float], y_pred: Sequence[float]) -> None:
    if len(y_true) != len(y_pred):
        raise ValueError(f"Разная длина: y_true={len(y_true)}, y_pred={len(y_pred)}")
    if len(y_true) == 0:
        raise ValueError("Пустые последовательности")
    for name, values in (("y_true", y_true), ("y_pred", y_pred)):
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"{name}: ожидаются только конечные значения")


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Root Mean Squared Error — дополнительная метрика качества (ADR 0002)."""
    _check_inputs(y_true, y_pred)
    squared = [(t - p) ** 2 for t, p in zip(y_true, y_pred, strict=True)]
    return math.sqrt(sum(squared) / len(squared))


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean Absolute Error — основная метрика качества проекта (ADR 0002)."""
    _check_inputs(y_true, y_pred)
    return sum(abs(t - p) for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)


def evaluate_regression(
    y_true: Sequence[float], y_pred: Sequence[float], reference: float
) -> dict[str, float]:
    """Оценить прогноз относительно постоянного reference — медианы цели train.

    При нулевой MAE точки отсчета mae_skill не определен: это бывает, когда
    вся цель test совпадает с reference. Вместо деления на ноль возвращается понятная ошибка.
    """
    model_mae = mae(y_true, y_pred)
    if not math.isfinite(reference):
        raise ValueError("reference: ожидается конечное значение")
    baseline_mae = mae(y_true, [reference] * len(y_true))
    if baseline_mae == 0:
        raise ValueError(
            "baseline_mae равен 0: mae_skill не определен для постоянной цели, "
            "совпадающей с reference"
        )
    return {
        "mae": model_mae,
        "rmse": rmse(y_true, y_pred),
        "baseline_mae": baseline_mae,
        "mae_skill": 1 - model_mae / baseline_mae,
    }
