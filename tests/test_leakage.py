
"""Проверки состава признаков и защиты от утечки цели."""

import json
from pathlib import Path

from housing_price.features import FEATURES, TARGET


def load_contract_columns():
    """Загрузить описание столбцов из контракта."""
    contract = json.loads(
        Path("data/contract.json").read_text(encoding="utf-8")
    )
    return contract["columns"]


def test_target_not_in_features():
    """Целевая переменная не должна быть признаком."""
    assert TARGET not in FEATURES


def test_features_match_contract():
    """Список признаков должен совпадать с контрактом."""
    columns = load_contract_columns()

    expected_features = {
        name
        for name, settings in columns.items()
        if settings["role"] == "feature"
    }

    assert len(FEATURES) == len(set(FEATURES))
    assert set(FEATURES) == expected_features


def test_single_target_matches_contract():
    """В контракте должна быть ровно одна правильная цель."""
    columns = load_contract_columns()

    contract_targets = [
        name
        for name, settings in columns.items()
        if settings["role"] == "target"
    ]

    assert contract_targets == [TARGET]
