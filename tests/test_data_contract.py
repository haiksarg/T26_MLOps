"""Тесты валидатора данных: успешная проверка и намеренно испорченные файлы."""

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from housing_price.validate_data import main

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "housing_sample.csv"
CONTRACT = ROOT / "data" / "contract.json"


def read_sample() -> tuple[list[str], list[dict[str, str]]]:
    with SAMPLE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def run_validator(
    tmp_path: Path, data: Path = SAMPLE, contract: Path = CONTRACT
) -> tuple[int, dict]:
    report_path = tmp_path / "reports" / "validation" / "report.json"
    code = main(
        ["--data", str(data), "--contract", str(contract), "--report", str(report_path)]
    )
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    return code, report


def failed_checks(report: dict) -> set[str]:
    return {check["name"] for check in report["checks"] if not check["passed"]}


def broken_copy(tmp_path: Path, mutate) -> Path:
    """Копия образца во временном каталоге, измененная функцией mutate(header, rows)."""
    header, rows = read_sample()
    header, rows = mutate(header, rows)
    return write_csv(tmp_path / "bad.csv", header, rows)


def test_sample_passes(tmp_path):
    code, report = run_validator(tmp_path)
    assert code == 0
    assert report["passed"] is True
    assert report["contract_version"] == "1.0.0"
    assert report["dataset"] == "california-housing-training-sample"
    assert report["rows"] == 40
    assert report["sha256"] == hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    assert all(check["passed"] for check in report["checks"])
    assert {"required_columns", "minimum_rows", "duplicate_rows"} <= {
        check["name"] for check in report["checks"]
    }


def test_report_sha256_matches_data_readme(tmp_path):
    _, report = run_validator(tmp_path)
    assert report["sha256"] in (ROOT / "data" / "README.md").read_text(encoding="utf-8")


def test_age_above_maximum_fails_range(tmp_path):
    def mutate(header, rows):
        rows[0]["housing_median_age"] = "53"
        return header, rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert report["passed"] is False
    assert failed_checks(report) == {"range:housing_median_age"}


def test_missing_target_column_fails_required_columns(tmp_path):
    def mutate(header, rows):
        return [name for name in header if name != "median_house_value"], rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert failed_checks(report) == {"required_columns"}


def test_unknown_ocean_proximity_fails_allowed_values(tmp_path):
    def mutate(header, rows):
        rows[3]["ocean_proximity"] = "DESERT"
        return header, rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert failed_checks(report) == {"allowed_values:ocean_proximity"}


def test_missing_population_fails_not_null(tmp_path):
    def mutate(header, rows):
        rows[2]["population"] = ""
        return header, rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert "not_null:population" in failed_checks(report)


def test_missing_total_bedrooms_is_allowed(tmp_path):
    def mutate(header, rows):
        rows[2]["total_bedrooms"] = ""
        return header, rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 0
    assert report["passed"] is True


def test_fractional_integer_fails_type(tmp_path):
    def mutate(header, rows):
        rows[1]["total_rooms"] = "10.5"
        return header, rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert failed_checks(report) == {"type:total_rooms"}


def test_non_numeric_value_fails_type(tmp_path):
    def mutate(header, rows):
        rows[1]["median_income"] = "high"
        return header, rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert "type:median_income" in failed_checks(report)


def test_extra_column_fails_unexpected_columns(tmp_path):
    def mutate(header, rows):
        for row in rows:
            row["listing_id"] = "1"
        return [*header, "listing_id"], rows

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert failed_checks(report) == {"unexpected_columns"}


def test_full_duplicate_fails_duplicate_rows(tmp_path):
    def mutate(header, rows):
        return header, [*rows, dict(rows[0])]

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert failed_checks(report) == {"duplicate_rows"}


def test_too_few_rows_fails_minimum_rows(tmp_path):
    def mutate(header, rows):
        return header, rows[:10]

    code, report = run_validator(tmp_path, broken_copy(tmp_path, mutate))
    assert code == 1
    assert failed_checks(report) == {"minimum_rows"}


def test_corrupted_contract_returns_2(tmp_path, capsys):
    contract = tmp_path / "contract.json"
    contract.write_text("{ это не JSON", encoding="utf-8")
    code, report = run_validator(tmp_path, contract=contract)
    assert code == 2
    assert report == {}
    assert "контракт" in capsys.readouterr().err


@pytest.mark.parametrize("missing_key", ["contract_version", "dataset", "columns"])
def test_contract_without_required_key_returns_2(tmp_path, missing_key):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    del contract[missing_key]
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    code, _ = run_validator(tmp_path, contract=path)
    assert code == 2


def test_missing_data_file_returns_2(tmp_path, capsys):
    code, _ = run_validator(tmp_path, data=tmp_path / "nope.csv")
    assert code == 2
    assert "nope.csv" in capsys.readouterr().err


def test_command_line_exit_codes(tmp_path):
    """Код завершения процесса: 0 для образца, 1 для испорченного файла."""

    def mutate(header, rows):
        rows[0]["housing_median_age"] = "53"
        return header, rows

    bad = broken_copy(tmp_path, mutate)
    base = [sys.executable, "-m", "housing_price.validate_data", "--contract", str(CONTRACT)]
    good_run = subprocess.run(
        [*base, "--data", str(SAMPLE), "--report", str(tmp_path / "ok.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    bad_run = subprocess.run(
        [*base, "--data", str(bad), "--report", str(tmp_path / "bad.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert good_run.returncode == 0
    assert bad_run.returncode == 1
    assert "range:housing_median_age" in bad_run.stderr

def test_report_is_written_with_lf_line_endings(tmp_path):
    """Отчет пишется с LF на любой ОС: иначе его MD5 в dvc.lock зависит от Windows/Linux."""
    report_path = tmp_path / "report.json"
    code = main(["--data", str(SAMPLE), "--contract", str(CONTRACT), "--report", str(report_path)])
    assert code == 0
    assert b"\r" not in report_path.read_bytes()
