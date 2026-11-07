"""Тесты предобработки: преобразования обучаются только на train."""

import json

import joblib
import numpy as np
import pandas as pd
import pytest
import yaml

from housing_price.features import FEATURES, TARGET
from housing_price.preprocess import NUMERIC_FEATURES, main, run

PARAMS = {"numeric_impute_strategy": "median", "scale_numeric": True}
TRAIN_CATEGORIES = ["INLAND", "NEAR BAY"] * 4


def make_frame(
    categories: list[str],
    shift: float = 0.0,
    missing_bedrooms: tuple[int, ...] = (),
) -> pd.DataFrame:
    """Маленькая таблица со всеми признаками и целью; shift сдвигает числовые значения."""
    count = len(categories)
    data: dict[str, list] = {}
    for position, name in enumerate(NUMERIC_FEATURES):
        data[name] = [float(10 * (position + 1) + i) + shift for i in range(count)]
    for row in missing_bedrooms:
        data["total_bedrooms"][row] = float("nan")
    data["ocean_proximity"] = categories
    data[TARGET] = [100_000.0 + 1_000.0 * i + shift for i in range(count)]
    return pd.DataFrame(data)[[*FEATURES, TARGET]]


def fitted_parts(preprocessor):
    numeric = preprocessor.named_transformers_["num"]
    return numeric.named_steps["imputer"], numeric.named_steps.get("scaler")


def test_scaling_and_imputation_statistics_come_from_train_only():
    """mean_ и statistics_ равны статистикам train и не равны статистикам train+test."""
    train = make_frame(TRAIN_CATEGORIES, missing_bedrooms=(1,))
    test = make_frame(["INLAND"] * 4, shift=500.0, missing_bedrooms=(0,))
    _, _, preprocessor, _ = run(train, test, PARAMS)
    imputer, scaler = fitted_parts(preprocessor)

    column = NUMERIC_FEATURES.index("longitude")
    combined = pd.concat([train, test])
    assert scaler.mean_[column] == pytest.approx(train["longitude"].mean())
    assert scaler.mean_[column] != pytest.approx(combined["longitude"].mean(), abs=1.0)

    bedrooms = NUMERIC_FEATURES.index("total_bedrooms")
    assert imputer.statistics_[bedrooms] == pytest.approx(train["total_bedrooms"].median())
    assert imputer.statistics_[bedrooms] != pytest.approx(
        combined["total_bedrooms"].median(), abs=1.0
    )


def test_train_is_centered_but_shifted_test_is_not():
    """Если бы масштабирование подгонялось по test, его среднее тоже стало бы нулевым."""
    train = make_frame(TRAIN_CATEGORIES)
    test = make_frame(["INLAND"] * 4, shift=500.0)
    train_out, test_out, _, _ = run(train, test, PARAMS)

    assert train_out["longitude"].mean() == pytest.approx(0.0, abs=1e-9)
    assert test_out["longitude"].mean() > 10.0


def test_test_values_do_not_change_fitted_statistics():
    """Два разных test дают одинаковые параметры преобразователя: fit их не видел."""
    train = make_frame(TRAIN_CATEGORIES, missing_bedrooms=(1,))
    mild_test = make_frame(["INLAND"] * 4, shift=1.0)
    extreme_test = make_frame(["INLAND"] * 4, shift=1_000_000.0, missing_bedrooms=(2,))

    _, _, first, _ = run(train, mild_test, PARAMS)
    _, _, second, _ = run(train, extreme_test, PARAMS)
    first_imputer, first_scaler = fitted_parts(first)
    second_imputer, second_scaler = fitted_parts(second)

    np.testing.assert_array_equal(first_imputer.statistics_, second_imputer.statistics_)
    np.testing.assert_array_equal(first_scaler.mean_, second_scaler.mean_)
    np.testing.assert_array_equal(first_scaler.scale_, second_scaler.scale_)


def test_no_missing_values_after_processing():
    """Пропуски есть и в train, и в test, а после обработки их нет."""
    train = make_frame(TRAIN_CATEGORIES, missing_bedrooms=(1, 5))
    test = make_frame(["INLAND"] * 4, shift=3.0, missing_bedrooms=(0,))
    assert train.isna().sum().sum() > 0
    assert test.isna().sum().sum() > 0

    train_out, test_out, _, report = run(train, test, PARAMS)

    assert train_out.isna().sum().sum() == 0
    assert test_out.isna().sum().sum() == 0
    assert report["missing_values_after"] == 0


def test_unknown_category_in_test_is_ignored():
    """Категория, которой нет в train, не ломает обработку и дает нули в one-hot."""
    train = make_frame(TRAIN_CATEGORIES)
    test = make_frame(["ISLAND", "INLAND"])

    _, test_out, _, _ = run(train, test, PARAMS)

    one_hot = [name for name in test_out.columns if name.startswith("ocean_proximity_")]
    assert sorted(one_hot) == ["ocean_proximity_INLAND", "ocean_proximity_NEAR BAY"]
    assert test_out.loc[0, one_hot].sum() == 0
    assert test_out.loc[1, "ocean_proximity_INLAND"] == 1


def test_target_is_not_a_feature_and_values_are_unchanged():
    """Цель не входит в признаки и записывается в результат без изменений."""
    train = make_frame(TRAIN_CATEGORIES, missing_bedrooms=(1,))
    test = make_frame(["INLAND"] * 4, shift=7.0)

    train_out, test_out, preprocessor, report = run(train, test, PARAMS)

    assert TARGET not in FEATURES
    assert TARGET not in preprocessor.get_feature_names_out()
    assert list(preprocessor.feature_names_in_) == FEATURES
    assert list(train_out.columns).count(TARGET) == 1
    assert list(train_out.columns)[-1] == TARGET
    assert list(train_out.columns)[:-1] == list(preprocessor.get_feature_names_out())
    assert report["n_features"] == len(train_out.columns) - 1
    np.testing.assert_array_equal(train_out[TARGET].to_numpy(), train[TARGET].to_numpy())
    np.testing.assert_array_equal(test_out[TARGET].to_numpy(), test[TARGET].to_numpy())


def test_scale_numeric_false_skips_scaler_and_keeps_units():
    """При scale_numeric=false масштабирования нет, значения остаются в исходных единицах."""
    train = make_frame(TRAIN_CATEGORIES)
    test = make_frame(["INLAND"] * 4, shift=500.0)

    train_out, _, preprocessor, _ = run(
        train, test, {"numeric_impute_strategy": "median", "scale_numeric": False}
    )
    _, scaler = fitted_parts(preprocessor)

    assert scaler is None
    np.testing.assert_allclose(train_out["longitude"].to_numpy(), train["longitude"].to_numpy())


def test_impute_strategy_is_taken_from_params():
    """Стратегия импутации берется из params.yaml и считается по train."""
    train = make_frame(TRAIN_CATEGORIES, missing_bedrooms=(0,))
    train.loc[1, "total_bedrooms"] = 1_000_000.0  # выброс: среднее и медиана расходятся
    test = make_frame(["INLAND"] * 4)
    column = NUMERIC_FEATURES.index("total_bedrooms")

    _, _, by_mean, _ = run(train, test, {"numeric_impute_strategy": "mean", "scale_numeric": True})
    _, _, by_median, _ = run(
        train, test, {"numeric_impute_strategy": "median", "scale_numeric": True}
    )
    mean_imputer, _ = fitted_parts(by_mean)
    median_imputer, _ = fitted_parts(by_median)

    assert mean_imputer.statistics_[column] == pytest.approx(train["total_bedrooms"].mean())
    assert median_imputer.statistics_[column] == pytest.approx(train["total_bedrooms"].median())
    assert mean_imputer.statistics_[column] != median_imputer.statistics_[column]


def test_cli_writes_processed_files_model_and_report(tmp_path, monkeypatch):
    """CLI читает split, пишет train/test, модель и отчет с согласованными числами."""
    train = make_frame(TRAIN_CATEGORIES, missing_bedrooms=(1,))
    test = make_frame(["ISLAND", "INLAND", "INLAND", "NEAR BAY"], shift=5.0, missing_bedrooms=(2,))
    split_dir = tmp_path / "split"
    processed_dir = tmp_path / "processed"
    split_dir.mkdir()
    train.to_csv(split_dir / "train.csv", index=False)
    test.to_csv(split_dir / "test.csv", index=False)

    params_path = tmp_path / "params.yaml"
    params_path.write_text(
        yaml.safe_dump(
            {
                "data": {"split_dir": str(split_dir), "processed_dir": str(processed_dir)},
                "preprocess": PARAMS,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)  # models/ и reports/ создаются относительно текущего каталога

    assert main(["--params", str(params_path)]) == 0

    train_out = pd.read_csv(processed_dir / "train.csv")
    test_out = pd.read_csv(processed_dir / "test.csv")
    report = json.loads((tmp_path / "reports" / "preprocess_metrics.json").read_text("utf-8"))
    preprocessor = joblib.load(tmp_path / "models" / "preprocessor.joblib")

    assert list(train_out.columns) == list(test_out.columns)
    assert list(train_out.columns)[-1] == TARGET
    assert report["train_rows"] == len(train_out) == len(train)
    assert report["test_rows"] == len(test_out) == len(test)
    assert report["n_features"] == len(train_out.columns) - 1
    assert report["missing_values_after"] == 0
    assert report["train_target_mean"] == pytest.approx(train[TARGET].mean())
    assert report["test_target_mean"] == pytest.approx(test[TARGET].mean())
    assert preprocessor.transform(test[FEATURES]).shape == (len(test), report["n_features"])


def test_text_outputs_use_lf_line_endings(tmp_path, monkeypatch):
    """CSV и отчет пишутся с LF на любой ОС: иначе MD5 в dvc.lock зависит от Windows/Linux."""
    train = make_frame(TRAIN_CATEGORIES)
    test = make_frame(["INLAND"] * 4, shift=5.0)
    split_dir = tmp_path / "split"
    processed_dir = tmp_path / "processed"
    split_dir.mkdir()
    train.to_csv(split_dir / "train.csv", index=False)
    test.to_csv(split_dir / "test.csv", index=False)
    params_path = tmp_path / "params.yaml"
    params_path.write_text(
        yaml.safe_dump(
            {
                "data": {"split_dir": str(split_dir), "processed_dir": str(processed_dir)},
                "preprocess": PARAMS,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert main(["--params", str(params_path)]) == 0

    for path in (
        processed_dir / "train.csv",
        processed_dir / "test.csv",
        tmp_path / "reports" / "preprocess_metrics.json",
    ):
        assert b"\r" not in path.read_bytes(), path.name
