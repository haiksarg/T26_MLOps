"""Тесты стратифицированного разделения данных."""

import pandas as pd
import yaml

from housing_price.split_data import main, split

SPLIT_PARAMS = {
    "test_size": 0.2,
    "random_state": 42,
    "stratify_column": "median_income",
    "stratify_bins": [0.0, 1.5, 3.0, 4.5, 6.0, float("inf")],
}


def make_data() -> pd.DataFrame:
    """Создать небольшой набор данных с пятью категориями дохода."""
    count = 100

    return pd.DataFrame(
        {
            "longitude": [-124.0 + i * 0.01 for i in range(count)],
            "latitude": [35.0] * count,
            "housing_median_age": [20.0] * count,
            "total_rooms": [1000.0] * count,
            "total_bedrooms": [200.0] * count,
            "population": [800.0] * count,
            "households": [300.0] * count,
            "median_income": [1.0, 2.0, 3.5, 5.0, 7.0] * 20,
            "median_house_value": [
                100_000 + i * 1000 for i in range(count)
            ],
            "ocean_proximity": ["INLAND"] * count,
        }
    )


def test_split_is_disjoint_and_complete():
    """Train и test не пересекаются и содержат все исходные строки."""
    df = make_data()
    train, test = split(df, SPLIT_PARAMS)

    assert set(train.index).isdisjoint(set(test.index))
    assert set(train.index) | set(test.index) == set(df.index)


def test_test_size():
    """Проверяем соотношение 80/20."""
    df = make_data()
    train, test = split(df, SPLIT_PARAMS)

    assert len(train) == 80
    assert len(test) == 20


def test_fixed_random_state():
    """Повторный запуск дает одинаковое разделение."""
    df = make_data()

    train1, test1 = split(df, SPLIT_PARAMS)
    train2, test2 = split(df, SPLIT_PARAMS)

    pd.testing.assert_frame_equal(train1, train2)
    pd.testing.assert_frame_equal(test1, test2)


def test_income_distribution_is_preserved():
    """Проверяем сохранение распределения категорий дохода."""
    df = make_data()
    _, test = split(df, SPLIT_PARAMS)

    bins = SPLIT_PARAMS["stratify_bins"]

    original_categories = pd.cut(
        df["median_income"],
        bins=bins,
        labels=False,
        include_lowest=True,
    )

    test_categories = pd.cut(
        test["median_income"],
        bins=bins,
        labels=False,
        include_lowest=True,
    )

    original_frequencies = (
        original_categories.value_counts(normalize=True).sort_index()
    )

    test_frequencies = (
        test_categories.value_counts(normalize=True).sort_index()
    )

    assert all(
        abs(original_frequencies - test_frequencies) <= 0.05
    )


def test_columns_are_unchanged_and_target_is_present():
    """Проверяем сохранение столбцов и целевой переменной."""
    df = make_data()
    train, test = split(df, SPLIT_PARAMS)

    assert list(train.columns) == list(df.columns)
    assert list(test.columns) == list(df.columns)

    assert "median_house_value" in train.columns
    assert "median_house_value" in test.columns

    assert "income_category" not in train.columns
    assert "income_category" not in test.columns


def test_cli_writes_two_csv_files(tmp_path):
    """Проверяем создание train.csv и test.csv."""
    df = make_data()

    raw_path = tmp_path / "housing.csv"
    split_dir = tmp_path / "split"
    params_path = tmp_path / "params.yaml"

    df.to_csv(raw_path, index=False)

    params_path.write_text(
        yaml.safe_dump(
            {
                "data": {
                    "raw": str(raw_path),
                    "split_dir": str(split_dir),
                },
                "split": SPLIT_PARAMS,
            }
        ),
        encoding="utf-8",
    )

    result = main(["--params", str(params_path)])

    assert result == 0

    train = pd.read_csv(split_dir / "train.csv")
    test = pd.read_csv(split_dir / "test.csv")

    assert train.shape == (80, 10)
    assert test.shape == (20, 10)

    assert list(train.columns) == list(df.columns)
    assert list(test.columns) == list(df.columns)
