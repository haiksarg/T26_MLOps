"""Общие fixtures: каждый тест получает новое состояние и пишет файлы только в tmp_path."""

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def sample_path() -> Path:
    """Эталонный образец. Тесты его только читают."""
    return ROOT / "data" / "housing_sample.csv"


@pytest.fixture
def contract_path() -> Path:
    return ROOT / "data" / "contract.json"


@pytest.fixture
def valid_frame(sample_path: Path) -> pd.DataFrame:
    """Новая копия корректного образца: 40 строк, проходит контракт."""
    return pd.read_csv(sample_path)


@pytest.fixture
def pipeline_frame(valid_frame: pd.DataFrame) -> pd.DataFrame:
    """Корректный набор для обучения: 120 разных строк.

    В образце в первом интервале дохода одна строка, для стратификации этого мало.
    total_rooms меняется, чтобы копии не стали полными дубликатами (их запрещает контракт).
    """
    copies = []
    for shift in range(3):
        copy = valid_frame.copy()
        copy["total_rooms"] = copy["total_rooms"] + shift
        copies.append(copy)
    return pd.concat(copies, ignore_index=True)


@pytest.fixture
def csv_factory(tmp_path: Path) -> Callable[..., Path]:
    """Записать DataFrame в CSV внутри tmp_path и вернуть путь."""

    def write(frame: pd.DataFrame, name: str = "input.csv") -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False, lineterminator="\n")
        return path

    return write


@pytest.fixture
def params() -> dict:
    """Параметры проекта с маленьким лесом и baseline: быстро и без зависимости от params.yaml."""
    config = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))
    config["train"] = {
        "model": "median_baseline",
        "seed": 42,
        "rf_n_estimators": 5,
        "rf_max_depth": 3,
    }
    return config
