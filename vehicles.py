ALLOWED_VEHICLES = [
    {"make": "MITSUBISHI", "model": "MONTERO",       "year_start": 1983, "year_end": 2006},
    {"make": "MITSUBISHI", "model": "MONTERO SPORT", "year_start": 1997, "year_end": 2004},
    {"make": "MITSUBISHI", "model": "MIGHTY MAX",    "year_start": 1982, "year_end": 1996},
    {"make": "DODGE",      "model": "RAIDER",        "year_start": 1987, "year_end": 1989},
    {"make": "DODGE",      "model": "RAM 50",        "year_start": 1979, "year_end": 1993},
    {"make": "DODGE",      "model": "D50",           "year_start": 1979, "year_end": 1980},
    {"make": "PLYMOUTH",   "model": "ARROW",         "year_start": 1979, "year_end": 1982},
]


def is_valid_vehicle(make, model, year):
    return any(
        v["make"] == make
        and v["model"] == model
        and v["year_start"] <= year <= v["year_end"]
        for v in ALLOWED_VEHICLES
    )
