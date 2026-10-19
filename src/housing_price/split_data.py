
"""Стратифицированное разделение данных до этапа предобработки."""

import argparse
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split


def split(
    df: pd.DataFrame,
    params: dict,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Разделить строки по категориям дохода, сохранив исходные столбцы."""
    income_category = pd.cut(
        df[params["stratify_column"]],
        bins=params["stratify_bins"],
        labels=False,
        include_lowest=True,
    )

    train, test = train_test_split(
        df,
        test_size=params["test_size"],
        random_state=params["random_state"],
        stratify=income_category,
    )

    return train, test


def main(argv: list[str] | None = None) -> int:
    """Прочитать параметры и сохранить train.csv и test.csv."""
    parser = argparse.ArgumentParser(
        description="Разделение California Housing на train/test"
    )
    parser.add_argument(
        "--params",
        default="params.yaml",
        help="Путь к файлу параметров",
    )
    args = parser.parse_args(argv)

    config = yaml.safe_load(
        Path(args.params).read_text(encoding="utf-8")
    )

    raw_path = Path(config["data"]["raw"])
    split_dir = Path(config["data"]["split_dir"])

    df = pd.read_csv(raw_path)
    train, test = split(df, config["split"])

    split_dir.mkdir(parents=True, exist_ok=True)

    train.to_csv(split_dir / "train.csv", index=False)
    test.to_csv(split_dir / "test.csv", index=False)

    print(f"train: {len(train)} rows; test: {len(test)} rows")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
