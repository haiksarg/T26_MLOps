# data/

| Файл | В Git | Назначение |
|---|---|---|
| `contract.json` | да | Машинный контракт данных — исполнимые правила проверки |
| `housing_sample.csv` | да | Разрешенный учебный образец (40 строк) |
| `raw/` | нет | Полный набор, скачивается по инструкции ниже |
| `processed/` | нет | Производные данные, воспроизводятся командами проекта |

Человеческое описание набора — назначение, лицензия, ограничения, стратегия разделения —
в [docs/data-card.md](../docs/data-card.md).

## Происхождение образца

| Что | Значение |
|---|---|
| Источник | `datasets/housing/housing.csv` из репозитория [ageron/handson-ml2](https://github.com/ageron/handson-ml2/tree/aa555aa16b9d0af6c84e67c7757f3317d05acb12/datasets/housing) |
| Версия источника | commit `aa555aa16b9d0af6c84e67c7757f3317d05acb12` |
| SHA-256 полного файла | `8a3727f4cf54ac1a327f69b1d5b4db54c5834ea81c6e4efc0d163300022a685e` (20 640 строк) |
| Способ построения | 40 случайных строк, `seed=42`, строки скопированы без изменений в исходном порядке |
| SHA-256 образца | `e11e3d0baa7263ed5e5407f5f3ad5c398b07c49d739bc816953fa958bee146f0` |

Пересобрать образец и убедиться, что он совпадает байт в байт:

```bash
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/ageron/handson-ml2/aa555aa16b9d0af6c84e67c7757f3317d05acb12/datasets/housing/housing.csv', 'data/raw/housing.csv')"
python -m housing_price.make_sample --source data/raw/housing.csv --output data/processed/housing_sample.csv --expected-sha256 8a3727f4cf54ac1a327f69b1d5b4db54c5834ea81c6e4efc0d163300022a685e
```

Вторая команда печатает SHA-256 образца — он должен совпасть со значением в таблице.
Каталог `data/raw/` должен существовать перед скачиванием (`mkdir data/raw` или `New-Item -ItemType Directory data/raw`).

Проверить SHA-256 файла в репозитории:

```bash
python -c "from pathlib import Path; import hashlib; print(hashlib.sha256(Path('data/housing_sample.csv').read_bytes()).hexdigest())"
```

Контрольная сумма связывает отчет валидации с конкретными байтами файла, но не доказывает его качество
или законность использования.
