"""Тесты обучения и журналирования запуска в MLflow."""

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from housing_price import train
from housing_price.models import make_estimator

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "housing_sample.csv"


def make_params(model: str = "median_baseline", seed: int = 42) -> dict:
    params = yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))
    params["train"] = {"model": model, "seed": seed}
    return params


@pytest.fixture
def frame() -> pd.DataFrame:
    # В образце в первом интервале дохода одна строка; для стратификации повторяем его трижды.
    return pd.concat([pd.read_csv(SAMPLE)] * 3, ignore_index=True)


def test_baseline_metrics_match_reference_point(frame):
    _, metrics, example = train.train_and_evaluate(frame, make_params())
    assert metrics["mae"] == pytest.approx(metrics["baseline_mae"])
    assert metrics["mae_skill"] == pytest.approx(0.0)
    assert metrics["train_rows"] + metrics["test_rows"] == len(frame)
    assert list(example.columns) == train.FEATURES


def test_same_seed_gives_same_metrics(frame):
    _, first, _ = train.train_and_evaluate(frame, make_params(seed=7))
    _, second, _ = train.train_and_evaluate(frame, make_params(seed=7))
    assert first == second


def test_unknown_model_is_rejected():
    with pytest.raises(ValueError, match="Неизвестная модель"):
        make_estimator("magic", 42, {})


def write_report(
    tmp_path: Path, data: Path, passed: bool = True, sha256: str | None = None
) -> Path:
    report = tmp_path / "raw.json"
    report.write_text(
        json.dumps(
            {
                "passed": passed,
                "sha256": sha256 or train.file_sha256(data),
                "contract_version": "1.0.0",
            }
        ),
        encoding="utf-8",
    )
    return report


def test_load_validated_data_returns_versions(tmp_path):
    df, versions = train.load_validated_data(SAMPLE, write_report(tmp_path, SAMPLE))
    assert len(df) == 40
    assert versions == {
        "data_sha256": train.file_sha256(SAMPLE),
        "contract_version": "1.0.0",
    }


def test_load_validated_data_rejects_failed_contract(tmp_path):
    with pytest.raises(ValueError, match="не прошел контракт"):
        train.load_validated_data(SAMPLE, write_report(tmp_path, SAMPLE, passed=False))


def test_load_validated_data_rejects_changed_file(tmp_path):
    with pytest.raises(ValueError, match="изменился после проверки"):
        train.load_validated_data(SAMPLE, write_report(tmp_path, SAMPLE, sha256="0" * 64))


def test_log_to_mlflow_records_versions_and_loadable_model(frame, tmp_path, monkeypatch):
    mlflow = pytest.importorskip("mlflow")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path / 'mlflow.db'}")
    monkeypatch.setenv("MLFLOW_EXPERIMENT", "test-housing")
    params = make_params(seed=7)
    model, metrics, example = train.train_and_evaluate(frame, params)
    versions = {"data_sha256": "a" * 64, "contract_version": "1.0.0"}

    record = train.log_to_mlflow(model, params, metrics, example, versions)

    run = mlflow.get_run(record["run_id"])
    assert run.info.run_name == "median_baseline-seed7"
    assert run.data.tags["data_sha256"] == "a" * 64
    assert run.data.tags["contract_version"] == "1.0.0"
    assert run.data.tags["seed"] == "7"
    assert "git_commit" in run.data.tags
    assert run.data.params["train.model"] == "median_baseline"
    assert run.data.metrics["mae"] == pytest.approx(metrics["mae"])
    run_record = json.loads(Path("reports/run.json").read_text(encoding="utf-8"))
    assert run_record["run_id"] == run.info.run_id

    loaded = mlflow.sklearn.load_model(record["model_uri"])
    assert loaded.predict(example).tolist() == model.predict(example).tolist()
