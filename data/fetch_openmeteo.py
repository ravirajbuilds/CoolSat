"""Fetch REAL average monthly night-time temperature across the CONUS from the
Open-Meteo Historical Weather (ERA5) archive, and write the JSON the CoolSat
visualization consumes.

Night-time temperature is approximated by the daily minimum 2 m air temperature
(`temperature_2m_min`) — the standard proxy for night-time / urban-heat-island
studies, since the diurnal minimum occurs a little before dawn. For each land
grid cell we pull the full daily series over the last 10 calendar years and
average it per calendar month.

The Open-Meteo archive API is free and needs no key, but is rate limited, so we
sample the grid at a coarser step than the demo by default and sleep between
calls. Run it where outbound HTTPS to `archive-api.open-meteo.com` is allowed
(it is blocked inside the CoolSat build container).

Usage:
    pip install requests
    python data/fetch_openmeteo.py                 # default coarse grid
    python data/fetch_openmeteo.py --step 0.8      # match the demo resolution
    python data/fetch_openmeteo.py --years 5
"""
import argparse
import json
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("This script needs `requests`:  pip install requests")

from us_region import (
    CITIES, CONUS_POLYGON, LAT_MAX, LAT_MIN, LON_MAX, LON_MIN,
    _frange, _point_in_polygon, month_labels,
)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OUT = os.path.join(os.path.dirname(__file__), "..", "viz", "data",
                   "us_nighttime_monthly.json")


def land_grid(step):
    lons = _frange(LON_MIN, LON_MAX, step)
    lats = _frange(LAT_MIN, LAT_MAX, step)
    cells = [(lat, lon) for lat in lats for lon in lons
             if _point_in_polygon(lon, lat, CONUS_POLYGON)]
    return cells


def fetch_cell(lat, lon, start_date, end_date, session, retries=4):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_min",
        "timezone": "auto",
        "temperature_unit": "celsius",
    }
    for attempt in range(retries):
        try:
            r = session.get(ARCHIVE_URL, params=params, timeout=60)
            if r.status_code == 429:
                time.sleep(2 ** attempt * 5)
                continue
            r.raise_for_status()
            d = r.json().get("daily", {})
            return d.get("time", []), d.get("temperature_2m_min", [])
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return [], []


def monthly_means(times, values, months):
    """Average daily values into a per-YYYY-MM series aligned to `months`."""
    buckets = {mm: [] for mm in months}
    for t, v in zip(times, values):
        if v is None:
            continue
        mm = t[:7]
        if mm in buckets:
            buckets[mm].append(v)
    out = []
    for mm in months:
        vals = buckets[mm]
        out.append(round(sum(vals) / len(vals) * 10) if vals else None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=float, default=1.5,
                    help="grid resolution in degrees (default 1.5; the demo uses 0.8)")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--end-year", type=int, default=2025)
    ap.add_argument("--sleep", type=float, default=0.4,
                    help="seconds to pause between API calls")
    args = ap.parse_args()

    end_year = args.end_year
    start_year = end_year - args.years + 1
    start_date = f"{start_year}-01-01"
    end_date = f"{end_year}-12-31"
    months = month_labels(start_year, end_year)

    cells = land_grid(args.step)
    print(f"fetching {len(cells)} cells x {args.years} yrs from Open-Meteo ...",
          file=sys.stderr)

    session = requests.Session()
    session.headers["User-Agent"] = "CoolSat/urban-heat (open-meteo archive)"

    grid = []
    for i, (lat, lon) in enumerate(cells, 1):
        times, values = fetch_cell(lat, lon, start_date, end_date, session)
        series = monthly_means(times, values, months)
        grid.append({"lat": round(lat, 3), "lon": round(lon, 3), "v": series})
        if i % 10 == 0 or i == len(cells):
            print(f"  {i}/{len(cells)}", file=sys.stderr)
        time.sleep(args.sleep)

    payload = {
        "meta": {
            "source": "Open-Meteo Historical Weather API (ERA5 reanalysis)",
            "variable": "average monthly night-time 2m temperature "
                        "(proxy: daily minimum temperature_2m_min)",
            "units": "°C",
            "value_scale": 0.1,
            "grid_step_deg": args.step,
            "start_year": start_year,
            "end_year": end_year,
            "generator": "fetch_openmeteo.py",
            "is_demo": False,
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
    print(f"wrote {OUT}  ({len(grid)} cells x {len(months)} months)",
          file=sys.stderr)


if __name__ == "__main__":
    main()
