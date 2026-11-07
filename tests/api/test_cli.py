import pytest

from housing_price import __version__
from housing_price.__main__ import main


def test_main_prints_smoke_check(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "RMSE=" in out


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out
