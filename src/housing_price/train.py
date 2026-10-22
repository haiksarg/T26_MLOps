"""Обучение модели и журналирование запуска в MLflow (ЛР4).

    python -m housing_price.train --params params.yaml            # стадия DVC, без MLflow
    python -m housing_price.train --params params.yaml --mlflow   # запуск эксперимента

Фактор эксперимента (``train.model``) и seed меняются только в params.yaml, код между
запусками не правится. seed задает разбиение train/test и случайность модели: внутри
одного seed варианты сравниваются на одном разбиении, а по нескольким seed оценивается
разброс метрики (ADR 0002).
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml
from sklearn.pipeline import Pipeline

from housing_price.features import FEATURES, TARGET
from housing_price.metrics import mae, rmse
from housing_price.models import SKOPS_TRUSTED_TYPES, make_estimator
from housing_price.preprocess import build_preprocessor
from housing_price.split_data import split

VALIDATION_REPORT = Path("reports/validation/raw.json")
MODEL_PATH = Path("models/model.joblib")
METRICS_PATH = Path("reports/train_metrics.json")
RUN_PATH = Path("reports/run.json")
DEFAULT_TRACKING_URI = "sqlite:///mlflow.db"
DEFAULT_EXPERIMENT = "housing-price"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_validated_data(raw_path: Path, report_path: Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """Прочитать полный набор, только если именно этот файл прошел контракт (стадия validate)."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not report["passed"]:
        raise ValueError(f"набор не прошел контракт данных, см. {report_path}")
    data_sha256 = file_sha256(raw_path)
    if data_sha256 != report["sha256"]:
        raise ValueError(f"{raw_path} изменился после проверки — выполните dvc repro validate")
    versions = {"data_sha256": data_sha256, "contract_version": report["contract_version"]}
    return pd.read_csv(raw_path), versions


def train_and_evaluate(
    df: pd.DataFrame, params: dict[str, Any]
) -> tuple[Pipeline, dict[str, float], pd.DataFrame]:
    """Разбить данные по seed, обучить pipeline на train и посчитать метрики на test."""
    train_params = params["train"]
    seed = train_params["seed"]
    train_df, test_df = split(df, {**params["split"], "random_state": seed})

    model = Pipeline(
        [
            ("preprocess", build_preprocessor(params["preprocess"])),
            ("model", make_estimator(train_params["model"], seed, train_params)),
        ]
    )
    model.fit(train_df[FEATURES], train_df[TARGET])

    y_true = test_df[TARGET].tolist()
    y_pred = model.predict(test_df[FEATURES]).tolist()
    # Точка отсчета MAE — прогноз медианой цены train для каждого района test.
    train_median = float(train_df[TARGET].median())
    baseline_mae = mae(y_true, [train_median] * len(y_true))
    model_mae = mae(y_true, y_pred)
    metrics = {
        "mae": model_mae,
        "rmse": rmse(y_true, y_pred),
        "baseline_mae": baseline_mae,
        "mae_skill": 1 - model_mae / baseline_mae,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
    }
    return model, metrics, test_df[FEATURES].head(5)


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def git_info() -> dict[str, str]:
    """Commit кода; git_dirty=true — есть незакоммиченные изменения кроме params.yaml и dvc.lock."""
    changes = _git(
        ["status", "--porcelain", "--untracked-files=no", "--", ".",
         ":(exclude)params.yaml", ":(exclude)dvc.lock"]
    )
    return {"git_commit": _git(["rev-parse", "HEAD"]), "git_dirty": str(bool(changes)).lower()}


def dvc_md5(dvc_file: Path) -> str:
    """MD5 полного набора из .dvc-файла — версия данных в терминах DVC."""
    if not dvc_file.exists():
        return "not-tracked"
    return str(yaml.safe_load(dvc_file.read_text(encoding="utf-8"))["outs"][0]["md5"])


def log_to_mlflow(
    model: Pipeline,
    params: dict[str, Any],
    metrics: dict[str, float],
    example: pd.DataFrame,
    versions: dict[str, str],
) -> dict[str, Any]:
    """Записать запуск в MLflow и сохранить его идентификатор в reports/run.json."""
    # MLflow импортируется здесь: стадия DVC без флага --mlflow работает и без него.
    import mlflow
    from mlflow.models import infer_signature

    train_params = params["train"]
    kind, seed = train_params["model"], train_params["seed"]
    experiment = os.getenv("MLFLOW_EXPERIMENT", DEFAULT_EXPERIMENT)
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", DEFAULT_TRACKING_URI))
    mlflow.set_experiment(experiment)

    with mlflow.start_run(run_name=f"{kind}-seed{seed}") as run:
        for section in ("train", "split", "preprocess"):
            mlflow.log_params({f"{section}.{key}": value for key, value in params[section].items()})
        mlflow.log_params({"split.effective_random_state": seed, "features": ",".join(FEATURES)})
        mlflow.log_metrics(metrics)
        mlflow.set_tags(
            {
                **git_info(),
                **versions,
                "dvc_md5": dvc_md5(Path(params["data"]["raw"] + ".dvc")),
                "model": kind,
                "seed": str(seed),
            }
        )
        signature = infer_signature(example, model.predict(example))
        model_info = mlflow.sklearn.log_model(
            model,
            name="model",
            signature=signature,
            input_example=example,
            skops_trusted_types=SKOPS_TRUSTED_TYPES.get(kind) or None,
        )

    record = {
        "experiment": experiment,
        "run_id": run.info.run_id,
        "run_name": run.info.run_name,
        "model_uri": model_info.model_uri,
        "metrics": metrics,
    }
    RUN_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUN_PATH.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Обучение модели стоимости жилья")
    parser.add_argument("--params", default="params.yaml", help="Путь к файлу параметров")
    parser.add_argument("--mlflow", action="store_true", help="Записать запуск в MLflow")
    args = parser.parse_args(argv)

    params = yaml.safe_load(Path(args.params).read_text(encoding="utf-8"))
    try:
        df, versions = load_validated_data(Path(params["data"]["raw"]), VALIDATION_REPORT)
    except (OSError, ValueError) as exc:
        print(f"данные не готовы: {exc}", file=sys.stderr)
        return 2

    model, metrics, example = train_and_evaluate(df, params)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n")

    name = f"{params['train']['model']}-seed{params['train']['seed']}"
    print(
        f"{name}: MAE={metrics['mae']:.1f}, baseline MAE={metrics['baseline_mae']:.1f}, "
        f"skill={metrics['mae_skill']:.4f}"
    )
    if args.mlflow:
        record = log_to_mlflow(model, params, metrics, example, versions)
        print(f"MLflow run {record['run_id']} ({record['experiment']}), {record['model_uri']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
