"""Smoke test HTTP API контейнера: готовность, прогноз и компактный JSON-отчет.

    python scripts/container_smoke.py --output reports/container/lr6-smoke.json

Нужна только стандартная библиотека Python. Отчет записывается после успешной проверки.
"""

import argparse
import http.client
import json
import math
import queue
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SAMPLE_REQUEST = {
    "longitude": -122.23,
    "latitude": 37.88,
    "housing_median_age": 41,
    "total_rooms": 880,
    "total_bedrooms": 129,
    "population": 322,
    "households": 126,
    "median_income": 8.3252,
    "ocean_proximity": "NEAR BAY",
}


class SmokeError(RuntimeError):
    """API не прошел smoke test."""


def positive_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError("timeout должен быть конечным числом больше 0")
    return seconds


def check_prediction(body: object) -> list[str]:
    """Пустой список означает корректный ответ регрессионной модели."""
    if not isinstance(body, dict):
        return ["ответ /predict должен быть JSON-объектом"]
    problems = []
    value = body.get("predicted_value")
    valid_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    if valid_number:
        try:
            valid_number = math.isfinite(value) and value > 0
        except OverflowError:
            valid_number = False
    if not valid_number:
        problems.append("predicted_value должен быть конечным положительным числом")
    for field in ("model_version", "request_id"):
        if not isinstance(body.get(field), str) or not body[field].strip():
            problems.append(f"{field} должен быть непустой строкой")
    return problems


def _read_json(url: str, timeout: float, payload: dict | None = None) -> object:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload, allow_nan=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    method = request.get_method()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise SmokeError(f"{method} {url}: HTTP {response.status}, ожидается 200")
            return json.load(response)
    except urllib.error.HTTPError as exc:
        exc.close()
        raise SmokeError(f"{method} {url}: HTTP {exc.code}, ожидается 200") from exc
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise SmokeError(f"{method} {url}: запрос или JSON-ответ некорректен") from exc


def request_json(url: str, timeout: float, payload: dict | None = None) -> object:
    # socket timeout не ограничивает DNS и все чтение тела целиком. Ожидание в основном
    # потоке ограничено отдельно; daemon не удерживает CLI при зависшем соединении.
    result = queue.Queue()

    def fetch():
        try:
            result.put((_read_json(url, timeout, payload), None))
        except Exception as exc:
            result.put((None, exc))

    threading.Thread(target=fetch, daemon=True).start()
    try:
        body, error = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise SmokeError(f"timeout: запрос {url} не завершен за {timeout:g} с") from exc
    if error is not None:
        raise error
    return body


def wait_ready(base_url: str, timeout: float = 30) -> None:
    """Опрос /readyz с общим сроком ожидания и короткими паузами."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise SmokeError("timeout должен быть конечным числом больше 0")
    deadline = time.monotonic() + timeout
    last_problem = "нет ответа /readyz"
    while (remaining := deadline - time.monotonic()) > 0:
        try:
            body = request_json(f"{base_url}/readyz", timeout=min(2, remaining))
            if (
                isinstance(body, dict)
                and body.get("status") == "ready"
                and time.monotonic() < deadline
            ):
                return
            last_problem = '/readyz не вернул {"status":"ready"}'
        except SmokeError as exc:
            last_problem = str(exc)
        time.sleep(min(0.1, max(0, deadline - time.monotonic())))
    raise SmokeError(f"timeout: /readyz не готов за {timeout:g} с; {last_problem}")


def run_smoke(base_url: str, timeout: float = 30) -> dict:
    # Адрес сохраняется в отчете: учетные данные и параметры URL в него не допускаются.
    parts = urllib.parse.urlsplit(base_url)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        raise SmokeError("base-url: нужен HTTP(S)-адрес без учетных данных, query и fragment")
    base_url = base_url.rstrip("/")
    wait_ready(base_url, timeout)
    body = request_json(f"{base_url}/predict", timeout=min(5, timeout), payload=SAMPLE_REQUEST)
    problems = check_prediction(body)
    if problems:
        raise SmokeError("; ".join(problems))
    return {"base_url": base_url, "request": SAMPLE_REQUEST, "response": body}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--timeout", type=positive_seconds, default=30.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run_smoke(args.base_url, args.timeout)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    except (SmokeError, OSError, ValueError) as exc:
        print(f"Smoke test: {exc}", file=sys.stderr)
        return 1
    print(f"Smoke test OK: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
