"""Валидатор данных по машинному контракту (ЛР2).

Запуск::

    python -m housing_price.validate_data --data data/housing_sample.csv \
        --contract data/contract.json --report reports/validation/lr2.json

Коды завершения:
    0 - все проверки пройдены;
    1 - нарушение данных (отчет записан, ``"passed": false``);
    2 - ошибка запуска: нет файла, поврежденный JSON, неполный контракт.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_DATA_VIOLATION = 1
EXIT_USAGE_ERROR = 2

REQUIRED_CONTRACT_KEYS = ("contract_version", "dataset", "columns")
KNOWN_TYPES = ("integer", "number", "string")
MAX_EXAMPLES = 5


class ContractError(Exception):
    """Контракт поврежден или не содержит обязательных ключей."""


def _check(name: str, passed: bool, details: str) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def _is_missing(value: str | None) -> bool:
    """Пустая строка (в том числе из одних пробелов) считается пропуском."""
    return value is None or value.strip() == ""


def _parse_number(text: str) -> float | None:
    """Конечное число или None. NaN, inf и записи вида 1_000 не принимаются."""
    if "_" in text:
        return None
    try:
        number = float(text.strip())
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _examples(row_numbers: list[int]) -> str:
    shown = ", ".join(str(n) for n in row_numbers[:MAX_EXAMPLES])
    suffix = ", ..." if len(row_numbers) > MAX_EXAMPLES else ""
    return f"строки файла: {shown}{suffix}"


def load_contract(path: Path) -> dict[str, Any]:
    """Читает контракт и проверяет его структуру. Ошибки - ContractError."""
    try:
        contract = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"не удалось прочитать контракт {path}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"контракт {path} поврежден: {exc}") from exc

    if not isinstance(contract, dict):
        raise ContractError("контракт должен быть JSON-объектом")
    missing = [key for key in REQUIRED_CONTRACT_KEYS if key not in contract]
    if missing:
        raise ContractError(f"в контракте нет обязательных ключей: {', '.join(missing)}")

    columns = contract["columns"]
    if not isinstance(columns, dict) or not columns:
        raise ContractError("ключ columns должен быть непустым объектом")
    for name, spec in columns.items():
        if not isinstance(spec, dict):
            raise ContractError(f"описание столбца {name} должно быть объектом")
        if spec.get("type") not in KNOWN_TYPES:
            raise ContractError(
                f"столбец {name}: type должен быть одним из {', '.join(KNOWN_TYPES)}"
            )
        for bound in ("minimum", "maximum"):
            value = spec.get(bound)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise ContractError(f"столбец {name}: {bound} должен быть числом")
        allowed = spec.get("allowed_values")
        if allowed is not None and not isinstance(allowed, list):
            raise ContractError(f"столбец {name}: allowed_values должен быть списком")
    minimum_rows = contract.get("minimum_rows", 0)
    if isinstance(minimum_rows, bool) or not isinstance(minimum_rows, int):
        raise ContractError("minimum_rows должен быть целым числом")
    return contract


def _read_table(raw: bytes) -> tuple[list[str], list[dict[str, str | None]]]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = list(reader)
    return list(reader.fieldnames or []), rows


def _column_checks(
    name: str, spec: dict[str, Any], rows: list[dict[str, str | None]]
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    # Номер строки в файле: заголовок - строка 1, первая запись - строка 2.
    numbered = [(index + 2, row.get(name)) for index, row in enumerate(rows)]
    present = [(number, value.strip()) for number, value in numbered if not _is_missing(value)]

    if spec.get("nullable") is False:
        empty = [number for number, value in numbered if _is_missing(value)]
        checks.append(
            _check(
                f"not_null:{name}",
                not empty,
                "пропусков нет" if not empty else f"пропусков: {len(empty)}, {_examples(empty)}",
            )
        )

    column_type = spec["type"]
    parsed: dict[int, float] = {}
    bad_type: list[int] = []
    for number, value in present:
        if column_type == "string":
            continue
        number_value = _parse_number(value)
        if number_value is None or (column_type == "integer" and not number_value.is_integer()):
            bad_type.append(number)
        else:
            parsed[number] = number_value
    checks.append(
        _check(
            f"type:{name}",
            not bad_type,
            f"все значения соответствуют типу {column_type}"
            if not bad_type
            else f"не соответствуют типу {column_type}: {len(bad_type)}, {_examples(bad_type)}",
        )
    )

    minimum, maximum = spec.get("minimum"), spec.get("maximum")
    if minimum is not None or maximum is not None:
        out_of_range = [
            number
            for number, number_value in parsed.items()
            if (minimum is not None and number_value < minimum)
            or (maximum is not None and number_value > maximum)
        ]
        low = "-inf" if minimum is None else minimum
        high = "+inf" if maximum is None else maximum
        bounds = f"[{low}; {high}]"
        checks.append(
            _check(
                f"range:{name}",
                not out_of_range,
                f"все значения в диапазоне {bounds}"
                if not out_of_range
                else f"вне диапазона {bounds}: {len(out_of_range)}, {_examples(out_of_range)}",
            )
        )

    allowed = spec.get("allowed_values")
    if allowed is not None:
        if column_type == "string":
            allowed_set = {str(item) for item in allowed}
            invalid = [number for number, value in present if value not in allowed_set]
        else:
            allowed_numbers = {float(item) for item in allowed if isinstance(item, int | float)}
            invalid = [
                number
                for number, _ in present
                if number not in parsed or parsed[number] not in allowed_numbers
            ]
        checks.append(
            _check(
                f"allowed_values:{name}",
                not invalid,
                "все значения допустимы"
                if not invalid
                else f"недопустимых значений: {len(invalid)}, {_examples(invalid)}",
            )
        )
    return checks


def validate(
    header: list[str], rows: list[dict[str, str | None]], contract: dict[str, Any]
) -> list[dict[str, Any]]:
    """Выполняет все проверки контракта и возвращает их результаты."""
    columns: dict[str, dict[str, Any]] = contract["columns"]
    checks: list[dict[str, Any]] = []

    missing = [name for name in columns if name not in header]
    checks.append(
        _check(
            "required_columns",
            not missing,
            "все столбцы контракта есть в файле"
            if not missing
            else f"нет столбцов: {', '.join(missing)}",
        )
    )

    if contract.get("allow_extra_columns") is False:
        extra = [name for name in header if name not in columns]
        checks.append(
            _check(
                "unexpected_columns",
                not extra,
                "лишних столбцов нет" if not extra else f"лишние столбцы: {', '.join(extra)}",
            )
        )

    minimum_rows = contract.get("minimum_rows", 0)
    enough = len(rows) >= minimum_rows
    checks.append(_check("minimum_rows", enough, f"{len(rows)} >= {minimum_rows}"))

    if contract.get("duplicate_rows") == "forbid":
        seen: dict[tuple[str | None, ...], int] = {}
        duplicates: list[int] = []
        for index, row in enumerate(rows):
            key = tuple(row.get(name) for name in header)
            if key in seen:
                duplicates.append(index + 2)
            else:
                seen[key] = index + 2
        checks.append(
            _check(
                "duplicate_rows",
                not duplicates,
                "полных дубликатов нет"
                if not duplicates
                else f"полных дубликатов: {len(duplicates)}, {_examples(duplicates)}",
            )
        )

    for name, spec in columns.items():
        if name in header:
            checks.extend(_column_checks(name, spec, rows))
    return checks


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": на Windows write_text иначе пишет CRLF, и MD5 отчета в dvc.lock другой.
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate_data",
        description="Проверка CSV-файла по машинному контракту данных.",
    )
    parser.add_argument("--data", type=Path, required=True, help="путь к CSV-файлу")
    parser.add_argument("--contract", type=Path, required=True, help="путь к contract.json")
    parser.add_argument("--report", type=Path, required=True, help="куда записать JSON-отчет")
    args = parser.parse_args(argv)

    try:
        contract = load_contract(args.contract)
        raw = args.data.read_bytes()
        header, rows = _read_table(raw)
    except ContractError as exc:
        print(f"ошибка контракта: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    except OSError as exc:
        print(f"не удалось прочитать файл данных {args.data}: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR
    except (UnicodeDecodeError, csv.Error) as exc:
        print(f"файл данных {args.data} не удалось разобрать как CSV: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    checks = validate(header, rows, contract)
    passed = all(check["passed"] for check in checks)
    report = {
        "contract_version": contract["contract_version"],
        "dataset": contract["dataset"],
        "data_file": args.data.as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rows": len(rows),
        "columns": header,
        "passed": passed,
        "checks": checks,
    }
    try:
        _write_report(args.report, report)
    except OSError as exc:
        print(f"не удалось записать отчет {args.report}: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    for check in checks:
        if not check["passed"]:
            print(f"FAIL {check['name']}: {check['details']}", file=sys.stderr)
    status = "пройдена" if passed else "не пройдена"
    print(f"проверка {status}: правил: {len(checks)}, sha256={report['sha256']}")
    return EXIT_OK if passed else EXIT_DATA_VIOLATION


if __name__ == "__main__":
    raise SystemExit(main())
