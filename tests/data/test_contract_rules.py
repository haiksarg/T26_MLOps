"""Параметризованные тесты правил контракта (ЛР5, issue #40).

Каждый файл создается только через fixture csv_factory во временном каталоге,
эталонный data/housing_sample.csv не изменяется.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from housing_price.validate_data import main


def run_validator(data: Path, contract: Path, tmp_path: Path) -> tuple[int, dict]:
    report_path = tmp_path / "reports" / "report.json"
    code = main(["--data", str(data), "--contract", str(contract), "--report", str(report_path)])
    return code, json.loads(report_path.read_text(encoding="utf-8"))


def failed_checks(report: dict) -> set[str]:
    return {check["name"] for check in report["checks"] if not check["passed"]}


def with_value(frame: pd.DataFrame, column: str, value: object, row: int = 0) -> pd.DataFrame:
    """Копия frame с одним измененным значением.

    Столбец переводится в object, чтобы остальные значения записались как есть
    (иначе float в целом столбце превратит 1234 в 1234.0 во всех строках).
    """
    changed = frame.copy()
    changed[column] = changed[column].astype(object)
    changed.loc[row, column] = value
    return changed


@pytest.mark.parametrize(
    ("column", "value", "rule"),
    [
        pytest.param(
            "housing_median_age", 53, "range:housing_median_age", id="range:housing_median_age"
        ),
        pytest.param("latitude", 42.1, "range:latitude", id="range:latitude"),
        pytest.param("longitude", -124.6, "range:longitude", id="range:longitude"),
        pytest.param("median_income", -0.1, "range:median_income", id="range:median_income"),
        pytest.param(
            "median_house_value", 500002, "range:median_house_value", id="range:median_house_value"
        ),
        pytest.param("total_rooms", 0, "range:total_rooms", id="range:total_rooms"),
        pytest.param("population", None, "not_null:population", id="not_null:population"),
        pytest.param("total_rooms", 10.5, "type:total_rooms", id="type:total_rooms"),
        pytest.param("median_income", "high", "type:median_income", id="type:median_income"),
        pytest.param("median_income", "inf", "type:median_income", id="type:median_income-inf"),
        pytest.param(
            "ocean_proximity",
            "DESERT",
            "allowed_values:ocean_proximity",
            id="allowed_values:ocean_proximity",
        ),
    ],
)
def test_single_violation_fails_exactly_its_rule(
    valid_frame, csv_factory, contract_path, tmp_path, column, value, rule
):
    data = csv_factory(with_value(valid_frame, column, value))

    code, report = run_validator(data, contract_path, tmp_path)

    assert code == 1
    assert report["passed"] is False
    assert failed_checks(report) == {rule}


@pytest.mark.parametrize(
    ("column", "value"),
    [
        pytest.param("housing_median_age", 52, id="housing_median_age=52-max"),
        pytest.param("housing_median_age", 0, id="housing_median_age=0-min"),
        pytest.param("latitude", 42.0, id="latitude=42.0-max"),
        pytest.param("latitude", 32.5, id="latitude=32.5-min"),
        pytest.param("longitude", -114.0, id="longitude=-114.0-max"),
        pytest.param("median_income", 15.0001, id="median_income=15.0001-max"),
        pytest.param("median_house_value", 500001, id="median_house_value=500001-max"),
        pytest.param("total_bedrooms", None, id="total_bedrooms-empty-nullable"),
        pytest.param("total_bedrooms", 0, id="total_bedrooms=0-min"),
    ],
)
def test_boundary_and_allowed_values_pass(
    valid_frame, csv_factory, contract_path, tmp_path, column, value
):
    data = csv_factory(with_value(valid_frame, column, value))

    code, report = run_validator(data, contract_path, tmp_path)

    assert code == 0
    assert report["passed"] is True
    assert failed_checks(report) == set()
