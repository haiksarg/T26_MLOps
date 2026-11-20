"""Отчет inspect образа ЛР6: image ID, размер, пользователь, healthcheck и содержимое /app.

    python scripts/container_inspect.py --output reports/container/lr6-inspect.txt

По умолчанию проверяется образ mlops-housing-price:lr6-<short-sha текущего commit>.
Скрипт сохраняет команды и их вывод и завершается с кодом 1, если образ нарушает требования ЛР6.
"""

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

IMAGE_NAME = "mlops-housing-price"
INSPECT_FORMAT = (
    "id={{.Id}} size={{.Size}} user={{.Config.User}} health={{json .Config.Healthcheck}}"
)
LIST_APP = (
    "import json; from pathlib import Path; "
    'print(json.dumps(sorted(p.name for p in Path("/app").iterdir())))'
)
# В runtime не должно быть ничего, кроме приложения и модели (раздел 14 задания).
FORBIDDEN_IN_APP = {
    ".git", ".env", "tests", "data", "reports", "mlruns", "mlartifacts", "mlflow.db", "src",
}


def run(args: list[str]) -> str:
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def short_sha() -> str:
    return run(["git", "rev-parse", "--short", "HEAD"])


def check_image(config: dict, revision: str, app_entries: list[str], commit: str) -> list[str]:
    """Нарушения требований ЛР6; пустой список — образ принят."""
    problems = []
    user = config.get("User", "")
    if not user or user.split(":")[0] in {"0", "root"}:
        problems.append(f"процесс запускается от root (User={user!r})")
    test = " ".join((config.get("Healthcheck") or {}).get("Test", []))
    if "/readyz" not in test:
        problems.append("healthcheck не проверяет /readyz")
    if not commit.startswith(revision) or len(revision) < 7:
        problems.append(f"метка revision {revision!r} не совпадает с commit {commit}")
    extra = sorted(FORBIDDEN_IN_APP.intersection(app_entries))
    if extra:
        problems.append(f"в /app лишние файлы: {', '.join(extra)}")
    if "models" not in app_entries:
        problems.append("в /app нет каталога models")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--image", help="тег образа; по умолчанию lr6-<short-sha> HEAD")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    commit = run(["git", "rev-parse", "HEAD"])
    image = args.image or f"{IMAGE_NAME}:lr6-{short_sha()}"
    summary_cmd = ["docker", "image", "inspect", image, "--format", INSPECT_FORMAT]
    revision_cmd = [
        "docker", "image", "inspect", image,
        "--format", '{{index .Config.Labels "org.opencontainers.image.revision"}}',
    ]
    list_cmd = ["docker", "run", "--rm", "--entrypoint", "python", image, "-c", LIST_APP]
    try:
        summary = run(summary_cmd)
        config = json.loads(run([*summary_cmd[:4], "--format", "{{json .Config}}"]))
        revision = run(revision_cmd)
        listing = run(list_cmd)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"не удалось проверить образ {image}: {exc}", file=sys.stderr)
        return 2

    app_entries = json.loads(listing)
    problems = check_image(config, revision, app_entries, commit)

    lines = [
        "# ЛР6: отчет inspect, получен командой",
        f"# python scripts/container_inspect.py --image {image} --output {args.output.as_posix()}",
        f"commit: {commit}",
        f"image: {image}",
        "",
        f"$ {shlex.join(summary_cmd)}",
        summary,
        "",
        f"$ {shlex.join(revision_cmd)}",
        revision,
        "",
        f"$ {shlex.join(list_cmd)}",
        listing,
        "",
        "result: " + ("OK" if not problems else "FAIL"),
        *[f"- {problem}" for problem in problems],
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
