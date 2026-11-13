import pytest

from housing_price.make_sample import main, make_sample, sha256_bytes

SOURCE = b"a,b\n" + b"".join(f"{i},x{i}\n".encode() for i in range(100))


def test_sample_is_deterministic_and_keeps_rows_verbatim():
    first = make_sample(SOURCE, rows=10, seed=42)
    assert first == make_sample(SOURCE, rows=10, seed=42)
    header, *rows = first.splitlines(keepends=True)
    assert header == b"a,b\n"
    assert len(rows) == 10
    assert all(row in SOURCE for row in rows)
    assert rows == sorted(rows, key=lambda r: int(r.split(b",")[0]))


def test_different_seed_gives_different_sample():
    assert make_sample(SOURCE, rows=10, seed=1) != make_sample(SOURCE, rows=10, seed=2)


def test_too_many_rows_is_rejected():
    with pytest.raises(ValueError, match="запрошено"):
        make_sample(SOURCE, rows=101, seed=42)


def test_main_rejects_unexpected_source_hash(tmp_path):
    source = tmp_path / "full.csv"
    source.write_bytes(SOURCE)
    output = tmp_path / "sample.csv"
    code = main(["--source", str(source), "--output", str(output), "--expected-sha256", "0" * 64])
    assert code == 1
    assert not output.exists()


def test_main_writes_sample(tmp_path):
    source = tmp_path / "full.csv"
    source.write_bytes(SOURCE)
    output = tmp_path / "out" / "sample.csv"
    args = ["--source", str(source), "--output", str(output), "--rows", "5"]
    assert main([*args, "--expected-sha256", sha256_bytes(SOURCE)]) == 0
    assert output.read_bytes() == make_sample(SOURCE, rows=5, seed=42)
