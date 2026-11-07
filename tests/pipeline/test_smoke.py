"""Интеграционный smoke-тест: validate -> train -> load -> predict во временном каталоге."""

import hashlib
import math
from pathlib import Path

import pytest
import yaml

from housing_price import train, validate_data
from housing_price.features import FEATURES


@pytest.fixture
def workspace(tmp_path, monkeypatch, params, pipeline_frame, csv_factory, contract_path):
    """Рабочий каталог проекта в tmp_path: данные, параметры, запуск стадий, как в dvc.yaml."""
    monkeypatch.chdir(tmp_path)
    params["data"]["raw"] = "data/raw/housing.csv"

    def write_params() -> None:
        Path("params.yaml").write_text(yaml.safe_dump(params), encoding="utf-8")

    def run_validate() -> int:
        return validate_data.main(
            [
                "--data", params["data"]["raw"],
                "--contract", str(contract_path),
                "--report", str(train.VALIDATION_REPORT),
            ]
        )

    def run_train() -> int:
        write_params()
        return train.main(["--params", "params.yaml"])

    csv_factory(pipeline_frame, params["data"]["raw"])
    return params, run_validate, run_train


@pytest.mark.parametrize("kind", ["median_baseline", "linear_regression", "random_forest"])
def test_validate_train_load_predict(workspace, pipeline_frame, kind):
    params, run_validate, run_train = workspace
    params["train"]["model"] = kind

    assert run_validate() == 0
    assert run_train() == 0

    bundle = train.load_bundle(train.MODEL_PATH)
    row = pipeline_frame.loc[[0], bundle["features"]]
    prediction = bundle["model"].predict(row)

    assert bundle["features"] == FEATURES
    assert prediction.shape == (1,)
    assert math.isfinite(float(prediction[0]))


def test_train_refuses_data_that_failed_contract(workspace, pipeline_frame, csv_factory):
    params, run_validate, run_train = workspace
    pipeline_frame.loc[0, "housing_median_age"] = 53
    csv_factory(pipeline_frame, params["data"]["raw"])

    assert run_validate() == 1
    assert run_train() == 2
    assert not train.MODEL_PATH.exists()


def test_train_refuses_data_changed_after_validation(workspace, pipeline_frame, csv_factory):
    params, run_validate, run_train = workspace
    assert run_validate() == 0

    pipeline_frame.loc[0, "total_rooms"] += 1
    csv_factory(pipeline_frame, params["data"]["raw"])

    assert run_train() == 2
    assert not train.MODEL_PATH.exists()


def test_train_refuses_when_validation_was_not_run(workspace):
    _, _, run_train = workspace
    assert run_train() == 2
    assert not train.MODEL_PATH.exists()


def test_smoke_run_leaves_reference_sample_unchanged(workspace, sample_path):
    _, run_validate, run_train = workspace
    before = hashlib.sha256(sample_path.read_bytes()).hexdigest()

    assert run_validate() == 0
    assert run_train() == 0

    assert hashlib.sha256(sample_path.read_bytes()).hexdigest() == before
