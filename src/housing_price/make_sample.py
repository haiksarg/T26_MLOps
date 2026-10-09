"""Воспроизводимое построение учебного образца из полного набора California Housing.

Строки копируются из источника без изменений (байт в байт), в исходном порядке:
`python -m housing_price.make_sample --source data/raw/housing.csv --output data/housing_sample.csv`
"""

import argparse
import hashlib
import random
import sys
from pathlib import Path

DEFAULT_ROWS = 40
DEFAULT_SEED = 42


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_sample(source: bytes, rows: int, seed: int) -> bytes:
    """Вернуть заголовок и `rows` случайных строк источника в исходном порядке."""
    header, *lines = source.splitlines(keepends=True)
    if rows > len(lines):
        raise ValueError(f"В источнике {len(lines)} строк данных, запрошено {rows}")
    picked = sorted(random.Random(seed).sample(range(len(lines)), rows))
    return header + b"".join(lines[i] for i in picked)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="housing-make-sample",
        description="Построить учебный образец из полного CSV California Housing.",
    )
    parser.add_argument("--source", type=Path, required=True, help="полный CSV источника")
    parser.add_argument("--output", type=Path, required=True, help="путь образца")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--expected-sha256", help="ожидаемый SHA-256 полного источника")
    args = parser.parse_args(argv)

    source = args.source.read_bytes()
    source_hash = sha256_bytes(source)
    if args.expected_sha256 and source_hash != args.expected_sha256.lower():
        print(
            f"SHA-256 источника {source_hash} не совпадает с ожидаемым {args.expected_sha256}",
            file=sys.stderr,
        )
        return 1

    sample = make_sample(source, args.rows, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(sample)
    print(f"source sha256: {source_hash}")
    print(f"sample sha256: {sha256_bytes(sample)} ({args.rows} rows, seed {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
