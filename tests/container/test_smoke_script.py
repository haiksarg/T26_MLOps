"""Smoke-скрипт: контракт ответа, HTTP-ошибки, таймаут и CLI без Docker."""

import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

GOOD = {
    "predicted_value": 432100.5,
    "model_version": "random_forest-seed42-data8a3727f4",
    "request_id": "smoke-test-request",
}


@pytest.fixture
def smoke(load_script):
    return load_script("container_smoke")


@pytest.fixture
def api_server():
    """Локальный HTTP-двойник: протокол тот же, модель и Docker не нужны."""
    state = {
        "ready_calls": 0,
        "not_ready_count": 0,
        "status": 200,
        "body": GOOD,
        "requests": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, body):
            time.sleep(state.get("response_delay", 0))
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            missing_bytes = state.get("truncated", 0) if self.path == "/predict" else 0
            self.send_header("Content-Length", str(len(data) + missing_bytes))
            self.end_headers()
            try:
                self.wfile.write(data)
            except BrokenPipeError:
                pass  # Клиент мог завершиться по timeout.

        def do_GET(self):
            assert self.path == "/readyz"
            state["ready_calls"] += 1
            if state["ready_calls"] <= state["not_ready_count"]:
                self.reply(503, {"detail": "модель не загружена"})
            else:
                self.reply(200, {"status": "ready"})

        def do_POST(self):
            assert self.path == "/predict"
            state["requests"].append(
                {
                    "content_type": self.headers["Content-Type"],
                    "body": json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                }
            )
            self.reply(state["status"], state["body"])

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


@pytest.mark.parametrize("value", [1, 432100.5])
def test_accepts_finite_positive_prediction(smoke, value):
    assert smoke.check_prediction({**GOOD, "predicted_value": value}) == []


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -float("inf"), -1, 0, "123", None, True, 10**400],
    ids=[
        "nan",
        "inf",
        "negative-inf",
        "negative",
        "zero",
        "string",
        "null",
        "bool",
        "overflow",
    ],
)
def test_rejects_invalid_prediction(smoke, value):
    assert any(
        "predicted_value" in p for p in smoke.check_prediction({**GOOD, "predicted_value": value})
    )


@pytest.mark.parametrize("field", ["model_version", "request_id", "predicted_value"])
def test_rejects_missing_required_field(smoke, field):
    body = {key: value for key, value in GOOD.items() if key != field}
    assert any(field in problem for problem in smoke.check_prediction(body))


@pytest.mark.parametrize("field", ["model_version", "request_id"])
@pytest.mark.parametrize("value", ["", "  ", None, 42])
def test_rejects_invalid_identifier(smoke, field, value):
    assert any(field in p for p in smoke.check_prediction({**GOOD, field: value}))


@pytest.mark.parametrize("body", [[], None, "ready", 123])
def test_rejects_response_that_is_not_object(smoke, body):
    assert smoke.check_prediction(body)


def test_closed_port_hits_readiness_deadline(smoke):
    started = time.monotonic()
    with pytest.raises(smoke.SmokeError, match="timeout.*readyz"):
        smoke.wait_ready("http://127.0.0.1:9", timeout=1)
    assert 0.9 <= time.monotonic() - started < 3


def test_slow_http_response_cannot_extend_deadline(smoke, api_server):
    base_url, state = api_server
    state["response_delay"] = 0.5
    started = time.monotonic()
    with pytest.raises(smoke.SmokeError, match="timeout"):
        smoke.wait_ready(base_url, timeout=0.1)
    assert time.monotonic() - started < 0.4


def test_rejects_late_readiness_response(smoke, monkeypatch):
    def late_response(*args, **kwargs):
        time.sleep(0.05)
        return {"status": "ready"}

    monkeypatch.setattr(smoke, "request_json", late_response)
    with pytest.raises(smoke.SmokeError, match="timeout"):
        smoke.wait_ready("http://127.0.0.1:8080", timeout=0.01)


def test_truncated_http_body_is_clear_failure(smoke, api_server, tmp_path, capsys):
    base_url, state = api_server
    state["truncated"] = 10
    assert (
        smoke.main(
            ["--base-url", base_url, "--timeout", "0.1", "--output", str(tmp_path / "unused.json")]
        )
        == 1
    )
    assert "JSON" in capsys.readouterr().err


def test_cli_writes_report_after_readiness_retry(smoke, api_server, tmp_path):
    base_url, state = api_server
    state["not_ready_count"] = 2
    output = tmp_path / "reports" / "smoke.json"
    # -I -S исключают пути проекта и site-packages: скрипту достаточно стандартной библиотеки.
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            smoke.__file__,
            "--base-url",
            base_url,
            "--timeout",
            "2",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert state["ready_calls"] == 3
    expected = {
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
    assert state["requests"] == [{"content_type": "application/json", "body": expected}]
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report == {"base_url": base_url, "request": expected, "response": GOOD}
    assert output.read_text().count("\n") == 1


@pytest.mark.parametrize(
    ("status", "body", "message"),
    [
        (201, GOOD, "HTTP 201"),
        (422, {"detail": "invalid features"}, "HTTP 422"),
        (503, {"detail": "модель не загружена"}, "HTTP 503"),
        (200, b"invalid json", "JSON"),
        (200, {**GOOD, "predicted_value": -1}, "predicted_value"),
        (200, {**GOOD, "request_id": ""}, "request_id"),
    ],
)
def test_cli_returns_failure_without_success_report(
    smoke, api_server, tmp_path, capsys, status, body, message
):
    base_url, state = api_server
    state.update(status=status, body=body)
    output = tmp_path / "smoke.json"
    assert smoke.main(["--base-url", base_url, "--output", str(output)]) != 0
    assert message in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf"])
def test_cli_rejects_invalid_timeout(smoke, tmp_path, timeout):
    with pytest.raises(SystemExit) as exc:
        smoke.main(["--timeout", timeout, "--output", str(tmp_path / "unused.json")])
    assert exc.value.code != 0


def test_cli_timeout_is_nonzero_and_leaves_no_report(smoke, tmp_path, capsys):
    output = tmp_path / "smoke.json"
    assert (
        smoke.main(
            [
                "--base-url",
                "http://127.0.0.1:9",
                "--timeout",
                "0.1",
                "--output",
                str(output),
            ]
        )
        != 0
    )
    assert "timeout" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize(
    "base_url",
    [
        "file:///tmp/test",
        "http://user:password@localhost",
        "http://localhost?token=example",
    ],
)
def test_rejects_urls_with_secrets_or_wrong_scheme(smoke, base_url):
    with pytest.raises(smoke.SmokeError, match="base-url"):
        smoke.run_smoke(base_url)
