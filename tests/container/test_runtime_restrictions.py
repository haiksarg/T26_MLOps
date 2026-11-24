"""Ограничения runtime ЛР6: Compose и .dockerignore проверяются как файлы, без Docker."""

import fnmatch
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_TEXT = (ROOT / "compose.yaml").read_text(encoding="utf-8")
APP = yaml.safe_load(COMPOSE_TEXT)["services"]["app"]
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def dockerignore_patterns() -> list[str]:
    """Паттерны .dockerignore без комментариев и пустых строк, без ведущего и концевого «/»."""
    lines = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    patterns = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return [pattern.strip("/") for pattern in patterns]


def copied_sources() -> list[str]:
    """Пути с хоста из команд COPY (без --from), включая .dockerignore."""
    sources = []
    for line in DOCKERFILE.splitlines():
        parts = line.split()
        if not parts or parts[0] != "COPY" or any(part.startswith("--from") for part in parts):
            continue
        paths = [part for part in parts[1:] if not part.startswith("--")]
        sources.extend(path.removeprefix("./").rstrip("/") for path in paths[:-1])
    return sources


def is_ignored(path: str, patterns: list[str]) -> bool:
    """Упрощенное правило Docker: паттерн исключает путь или любой каталог на пути к нему."""
    parts = path.split("/")
    prefixes = ["/".join(parts[: index + 1]) for index in range(len(parts))]
    for pattern in patterns:
        if pattern.startswith("**/"):
            tail = pattern.removeprefix("**/")
            if any(fnmatch.fnmatchcase(part, tail) for part in parts):
                return True
        elif any(fnmatch.fnmatchcase(prefix, pattern) for prefix in prefixes):
            return True
    return False


# ---------- Compose: ограничения процесса ----------


def test_root_filesystem_is_read_only():
    assert APP.get("read_only") is True


def test_tmp_is_a_size_limited_tmpfs():
    mounts = APP.get("tmpfs", [])
    mounts = [mounts] if isinstance(mounts, str) else mounts
    tmp = [mount for mount in mounts if mount.split(":")[0] == "/tmp"]

    assert len(tmp) == 1, "в /tmp должен быть смонтирован tmpfs"
    assert "size=" in tmp[0], "размер tmpfs ограничен: иначе запись в память не ограничена"


def test_only_tmp_is_writable():
    mounts = APP.get("tmpfs", [])
    mounts = [mounts] if isinstance(mounts, str) else mounts

    assert [mount.split(":")[0] for mount in mounts] == ["/tmp"]
    assert "volumes" not in APP, "bind mount или volume дали бы запись вне /tmp"


def test_all_capabilities_are_dropped_and_none_added():
    assert APP.get("cap_drop") == ["ALL"]
    assert "cap_add" not in APP


def test_new_privileges_are_forbidden():
    assert "no-new-privileges:true" in APP.get("security_opt", [])


def test_container_is_neither_privileged_nor_root():
    assert not APP.get("privileged")
    assert str(APP.get("user", "10001")).split(":")[0] not in {"root", "0"}


def test_docker_socket_is_not_exposed():
    assert "docker.sock" not in COMPOSE_TEXT


def test_ports_are_published_on_loopback_only():
    ports = APP["ports"]

    assert ports
    assert all(str(port).startswith("127.0.0.1:") for port in ports)


# ---------- .dockerignore ----------


@pytest.mark.parametrize(
    "entry",
    [".git", ".env", ".env.*", "models", "reports", "mlruns", "mlflow.db", ".dvc"],
)
def test_dockerignore_excludes_secrets_and_local_artifacts(entry):
    assert entry in dockerignore_patterns()


@pytest.mark.parametrize("entry", ["data/split", "data/processed"])
def test_dockerignore_excludes_regenerated_data(entry):
    assert entry in dockerignore_patterns()


@pytest.mark.parametrize(
    "entry", ["src", "tests", "scripts", "data", "*", "**", "data/*", "data/**"]
)
def test_dockerignore_does_not_exclude_what_the_build_needs(entry):
    assert entry not in dockerignore_patterns()


def test_dockerignore_does_not_exclude_any_copied_path():
    patterns = dockerignore_patterns()
    sources = copied_sources()

    assert ".dockerignore" in sources, "тесты в quality-стадии читают .dockerignore"
    assert "data/raw/housing.csv" in sources
    assert [path for path in sources if is_ignored(path, patterns)] == []


def test_dockerignore_matcher_detects_an_excluded_source():
    assert is_ignored("data/raw/housing.csv", ["data"])
    assert is_ignored("src/housing_price/__pycache__", ["**/__pycache__"])
    assert not is_ignored("data/raw/housing.csv", ["data/split", "data/processed"])
