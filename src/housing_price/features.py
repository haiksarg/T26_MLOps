
"""Список признаков для модели прогнозирования стоимости жилья.

Целевая переменная хранится отдельно и не используется
в качестве входного признака во избежание утечки.
"""

TARGET = "median_house_value"

FEATURES = [
    "longitude",
    "latitude",
    "housing_median_age",
    "total_rooms",
    "total_bedrooms",
    "population",
    "households",
    "median_income",
    "ocean_proximity",
]
