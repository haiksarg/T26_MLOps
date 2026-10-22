"""Модели эксперимента ЛР4. Вид модели — фактор эксперимента (params.yaml → train.model)."""

from typing import Any

from sklearn.base import RegressorMixin
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

MODEL_KINDS = ("median_baseline", "linear_regression", "random_forest")

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
    "linear_regression": [*PIPELINE_TRUSTED_TYPES],
    # Tree хранит узлы, пороги и значения листьев обученных деревьев леса.
    # skops не проверяет корректность внутренних индексов: разрешаем этот тип
    # для созданных нами артефактов, а не для моделей неизвестного происхождения.
    "random_forest": [*PIPELINE_TRUSTED_TYPES, "sklearn.tree._tree.Tree"],
}


def make_estimator(kind: str, seed: int, params: dict[str, Any]) -> RegressorMixin:
    """Создать необученную модель по виду из params.yaml."""
    if kind == "median_baseline":
        # Точка отсчета: прогноз — медиана цены по train для любого района.
        return DummyRegressor(strategy="median")
    if kind == "linear_regression":
        return LinearRegression()
    if kind == "random_forest":
        return RandomForestRegressor(
            n_estimators=params["rf_n_estimators"],
            max_depth=params["rf_max_depth"],
            random_state=seed,
            n_jobs=-1,
        )
    raise ValueError(f"Неизвестная модель {kind!r}; допустимые: {', '.join(MODEL_KINDS)}")
