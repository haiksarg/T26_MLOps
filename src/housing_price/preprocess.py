"""Предобработка признаков: все преобразования обучаются только на train.

Импутация пропусков, масштабирование и кодирование категорий вычисляют
статистики по обучающей выборке и затем применяются к тестовой. Так
информация из test не попадает в обучение (docs/data-card.md, раздел 8).

Запуск: ``python -m housing_price.preprocess --params params.yaml``
"""

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from housing_price.features import FEATURES, TARGET

CATEGORICAL_FEATURES = ["ocean_proximity"]
NUMERIC_FEATURES = [name for name in FEATURES if name not in CATEGORICAL_FEATURES]

MODEL_PATH = Path("models/preprocessor.joblib")
REPORT_PATH = Path("reports/preprocess_metrics.json")


def build_preprocessor(params: dict[str, Any]) -> ColumnTransformer:
    """Собрать необученный преобразователь по секции ``preprocess`` из params.yaml."""
    numeric_steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy=params["numeric_impute_strategy"])),
    ]
    if params["scale_numeric"]:
        numeric_steps.append(("scaler", StandardScaler()))

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline(numeric_steps), NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ],
        verbose_feature_names_out=False,
    )
    preprocessor.set_output(transform="pandas")
    return preprocessor


def _with_target(features: pd.DataFrame, source: pd.DataFrame) -> pd.DataFrame:
    """Вернуть преобразованные признаки и столбец цели без изменений."""
    result = features.reset_index(drop=True)
    result[TARGET] = source[TARGET].to_numpy()
    return result


def run(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    params: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, ColumnTransformer, dict[str, float]]:
    """Обучить преобразователь на train и применить его к train и test."""
    preprocessor = build_preprocessor(params)
    # fit видит только обучающую выборку; test участвует лишь в transform.
    preprocessor.fit(train_df[FEATURES])

    train_out = _with_target(preprocessor.transform(train_df[FEATURES]), train_df)
    test_out = _with_target(preprocessor.transform(test_df[FEATURES]), test_df)

    feature_names = list(preprocessor.get_feature_names_out())
    report = {
        "train_rows": len(train_out),
        "test_rows": len(test_out),
        "n_features": len(feature_names),
        "missing_values_after": int(
            train_out[feature_names].isna().sum().sum() + test_out[feature_names].isna().sum().sum()
        ),
        "train_target_mean": float(train_out[TARGET].mean()),
        "test_target_mean": float(test_out[TARGET].mean()),
    }
    return train_out, test_out, preprocessor, report


def main(argv: list[str] | None = None) -> int:
    """Прочитать split, выполнить предобработку и сохранить результаты."""
    parser = argparse.ArgumentParser(
        description="Предобработка признаков: fit на train, transform на train и test"
    )
    parser.add_argument("--params", default="params.yaml", help="Путь к файлу параметров")
    args = parser.parse_args(argv)

    config = yaml.safe_load(Path(args.params).read_text(encoding="utf-8"))
    split_dir = Path(config["data"]["split_dir"])
    processed_dir = Path(config["data"]["processed_dir"])

    train_df = pd.read_csv(split_dir / "train.csv")
    test_df = pd.read_csv(split_dir / "test.csv")

    train_out, test_out, preprocessor, report = run(train_df, test_df, config["preprocess"])

    processed_dir.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Явный "\n": иначе на Windows pandas и write_text пишут CRLF, и контрольные суммы DVC
    # (dvc.lock) отличаются от полученных на Linux при тех же данных.
    train_out.to_csv(processed_dir / "train.csv", index=False, lineterminator="\n")
    test_out.to_csv(processed_dir / "test.csv", index=False, lineterminator="\n")
    joblib.dump(preprocessor, MODEL_PATH)
    with REPORT_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(report, indent=2) + "\n")

    print(
        f"train: {report['train_rows']} rows; test: {report['test_rows']} rows; "
        f"features: {report['n_features']}; missing after: {report['missing_values_after']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
