"""Generate a PHYSICALLY-GROUNDED DEMO dataset of average monthly night-time
temperature across the CONUS, 2016-2025, matching the exact JSON schema that the
live Open-Meteo fetcher emits.

This exists so the visualization is fully interactive offline / where the
Open-Meteo API is not reachable. The values are a deterministic climatology model
(latitude gradient, elevation/continentality proxies, seasonal cycle, a decadal
warming trend, ENSO-like interannual wobble, and urban-heat-island offsets) — they
are realistic in shape but are NOT observations. Replace with real data via:

    python data/fetch_openmeteo.py

Usage:
    python data/gen_demo_data.py            # -> viz/data/us_nighttime_monthly.json
"""
import json
import math
import os

from us_region import (
    CITIES, CONUS_POLYGON, GRID_STEP, land_grid, month_labels,
)

START_YEAR, END_YEAR = 2016, 2025
OUT = os.path.join(os.path.dirname(__file__), "..", "viz", "data",
                   "us_nighttime_monthly.json")


def mountain_cool(lon, lat):
    """Crude cooling from elevation over the mountain West (Rockies core near
    -111, Sierra/Cascades near -120, high plains ramp)."""
    rockies = 5.0 * math.exp(-((lon + 111.0) / 6.0) ** 2)
    sierra = 2.5 * math.exp(-((lon + 120.0) / 3.0) ** 2)
    plains = 2.0 * max(0.0, (-100.0 - lon) / 15.0) if lon < -100 else 0.0
    return rockies + sierra + min(plains, 3.0)


def interior_bonus(lon):
    """Extra seasonal amplitude inland (continentality), peaking mid-continent."""
    return 4.0 * math.exp(-((lon + 98.0) / 14.0) ** 2)


def uhi_offset(lat, lon):
    total = 0.0
    for _name, clat, clon, strength in CITIES:
        d2 = ((lat - clat)) ** 2 + ((lon - clon) * math.cos(math.radians(lat))) ** 2
        total += strength * math.exp(-d2 / (0.6 ** 2))
    return total


def night_temp(lat, lon, year, month):
    """Modelled average night-time (proxy: daily-minimum) 2m temperature, °C."""
    annual_mean = 22.0 - 0.72 * (lat - 25.0)
    annual_mean -= mountain_cool(lon, lat)

    amp = 9.0 + 0.28 * (lat - 25.0) + interior_bonus(lon)
    seasonal = amp * math.cos(2.0 * math.pi * (month - 7) / 12.0)  # peak in July

    trend = 0.032 * (year - START_YEAR)                 # ~+0.3 C over the decade
    enso = 0.6 * math.sin(2.0 * math.pi * (year - START_YEAR) / 3.3)
    texture = 0.4 * math.sin(lat * 3.1 + lon * 2.7)     # deterministic micro-relief

    return annual_mean + seasonal + trend + enso + texture + uhi_offset(lat, lon)


def main():
    lons, lats, cells = land_grid()
    months = month_labels(START_YEAR, END_YEAR)

    grid = []
    for (lat, lon) in cells:
        series = []
        for label in months:
            y, m = int(label[:4]), int(label[5:])
            v = night_temp(lat, lon, y, m)
            series.append(round(v * 10))          # store tenths-of-°C as int
        grid.append({"lat": round(lat, 3), "lon": round(lon, 3), "v": series})

    payload = {
        "meta": {
            "source": "DEMO climatology model (synthetic) — not observations",
            "variable": "average monthly night-time 2m temperature "
                        "(proxy: daily minimum)",
            "units": "°C",
            "value_scale": 0.1,
            "grid_step_deg": GRID_STEP,
            "start_year": START_YEAR,
            "end_year": END_YEAR,
            "generator": "gen_demo_data.py",
            "is_demo": True,
        },
        "months": months,
        "polygon": [[round(lo, 3), round(la, 3)] for lo, la in CONUS_POLYGON],
        "cities": [{"name": n, "lat": la, "lon": lo}
                   for (n, la, lo, _s) in CITIES],
        "grid": grid,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    size_kb = os.path.getsize(OUT) / 1024
    print(f"wrote {OUT}  ({len(grid)} cells x {len(months)} months, "
          f"{size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
