"""Проверки отчета inspect (scripts/container_inspect.py) на подготовленной конфигурации образа."""

import pytest

COMMIT = "5b036c8a1e1c1a6d1b6c59c2f0bfa7a3c2a9e001"
GOOD = {
    "User": "10001:10001",
    "Healthcheck": {"Test": ["CMD", "python", "-c", "urlopen('http://127.0.0.1:8080/readyz')"]},
}


@pytest.fixture
def check_image(load_script):
    return load_script("container_inspect").check_image


def test_accepts_image_built_by_dockerfile(check_image):
    assert check_image(GOOD, COMMIT, ["models"], COMMIT) == []


@pytest.mark.parametrize("user", ["", "0", "root", "0:0"])
def test_rejects_root_user(check_image, user):
    problems = check_image({**GOOD, "User": user}, COMMIT, ["models"], COMMIT)
    assert any("root" in problem for problem in problems)


def test_rejects_healthcheck_without_readyz(check_image):
    config = {**GOOD, "Healthcheck": {"Test": ["CMD", "python", "-c", "urlopen('/healthz')"]}}
    assert any("/readyz" in problem for problem in check_image(config, COMMIT, ["models"], COMMIT))


@pytest.mark.parametrize("revision", ["unknown", "", "1234567"])
def test_rejects_image_not_linked_to_commit(check_image, revision):
    assert any("revision" in p for p in check_image(GOOD, revision, ["models"], COMMIT))


@pytest.mark.parametrize("extra", [".git", ".env", "tests", "data", "mlruns", "reports"])
def test_rejects_extra_files_in_app(check_image, extra):
    problems = check_image(GOOD, COMMIT, ["models", extra], COMMIT)
    assert any(extra in problem for problem in problems)


def test_rejects_image_without_model_dir(check_image):
    assert any("models" in problem for problem in check_image(GOOD, COMMIT, [], COMMIT))
