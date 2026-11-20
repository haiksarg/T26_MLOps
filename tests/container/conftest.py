"""Fixtures слоя container: скрипты из scripts/ загружаются как модули, без Docker."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def load_script():
    def load(name: str):
        path = ROOT / "scripts" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"scripts_{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module

    return load
