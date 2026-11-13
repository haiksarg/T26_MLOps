import math

import pytest

from housing_price.metrics import mae, rmse


def test_rmse_zero_for_perfect_prediction():
    assert rmse([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0


def test_rmse_known_value():
    # ошибки 3 и 4 -> sqrt((9 + 16) / 2)
    assert rmse([0.0, 0.0], [3.0, 4.0]) == pytest.approx(math.sqrt(12.5))


def test_mae_known_value():
    assert mae([0.0, 0.0], [3.0, -4.0]) == pytest.approx(3.5)


@pytest.mark.parametrize("metric", [rmse, mae])
def test_metrics_reject_length_mismatch(metric):
    with pytest.raises(ValueError, match="Разная длина"):
        metric([1.0, 2.0], [1.0])


@pytest.mark.parametrize("metric", [rmse, mae])
def test_metrics_reject_empty_input(metric):
    with pytest.raises(ValueError, match="Пустые"):
        metric([], [])
