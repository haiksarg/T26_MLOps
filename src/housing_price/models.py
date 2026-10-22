"""Модели эксперимента ЛР4. Вид модели — фактор эксперимента (params.yaml → train.model)."""

from typing import Any

from sklearn.base import RegressorMixin
from sklearn.dummy import DummyRegressor

MODEL_KINDS = ("median_baseline",)

# Типы, которые skops по умолчанию не доверяет, но которые команда проверила.
# Список получен на обученном pipeline командой
# skops.io.get_untrusted_types(data=skops.io.dumps(model)) и передается в mlflow.sklearn.log_model.
# Переход на pickle запрещен: он отключает проверку типов при загрузке модели.
#
# Общий для всех моделей: SimpleImputer в предобработке хранит тип данных train
# (_fit_dtype и _fill_dtype = dtype('float64')). numpy.dtype — описание числового типа
# без исполняемого кода, поэтому его загрузка безопасна.
PIPELINE_TRUSTED_TYPES = ["numpy.dtype"]

SKOPS_TRUSTED_TYPES: dict[str, list[str]] = {
    "median_baseline": [*PIPELINE_TRUSTED_TYPES],
}


def make_estimator(kind: str, seed: int, params: dict[str, Any]) -> RegressorMixin:
    """Создать необученную модель по виду из params.yaml."""
    if kind == "median_baseline":
        # Точка отсчета: прогноз — медиана цены по train для любого района.
        return DummyRegressor(strategy="median")
    raise ValueError(f"Неизвестная модель {kind!r}; допустимые: {', '.join(MODEL_KINDS)}")
