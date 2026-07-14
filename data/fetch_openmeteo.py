"""Fetch REAL average monthly night-time temperature across the CONUS from the
Open-Meteo Historical Weather (ERA5) archive, and write the JSON the CoolSat
visualization consumes.

Night-time temperature is approximated by the daily minimum 2 m air temperature
(`temperature_2m_min`) — the standard proxy for night-time / urban-heat-island
studies, since the diurnal minimum occurs a little before dawn. For each land
grid cell we pull the full daily series over the last 10 calendar years and
average it per calendar month.

To stay within Open-Meteo's free-tier limits, we request **many locations per
HTTP call** (comma-separated coordinates) instead of one call per cell — this
slashes the request count and finishes in a couple of minutes. The API call
*weight* still scales with locations x years, so keep the grid coarse enough
that (cells x years) stays comfortably under the ~10k/day free quota; the
default 1.5 deg grid (~370 cells x 10 yr) is well within it.

Run it where outbound HTTPS to `archive-api.open-meteo.com` is allowed (it is
blocked inside the CoolSat build container — see the GitHub Actions workflow,
which runs this on a GitHub-hosted runner).

Usage:
    pip install requests
    python data/fetch_openmeteo.py                 # 1.5 deg grid, 10 yr
    python data/fetch_openmeteo.py --step 1.0      # finer (more quota/time)
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
    return [(lat, lon) for lat in lats for lon in lons
            if _point_in_polygon(lon, lat, CONUS_POLYGON)]


def fetch_batch(batch, start_date, end_date, session, retries=6):
    """Fetch one batch of (lat, lon) points in a single multi-location request.

    Open-Meteo returns a JSON object for a single location and a JSON array for
    many; normalise to a list aligned with `batch` order.
    """
    params = {
        "latitude": ",".join(f"{la:.4f}" for la, _ in batch),
        "longitude": ",".join(f"{lo:.4f}" for _, lo in batch),
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_min",
        "timezone": "auto",
        "temperature_unit": "celsius",
    }
    for attempt in range(retries):
        try:
            r = session.get(ARCHIVE_URL, params=params, timeout=120)
            if r.status_code == 429:                      # rate limited
                time.sleep(min(60, 2 ** attempt * 3))
                continue
            r.raise_for_status()
            payload = r.json()
            return payload if isinstance(payload, list) else [payload]
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


def monthly_means(daily, months):
    """Average a location's daily series into a per-YYYY-MM list aligned to
    `months`. `daily` is the Open-Meteo per-location {time, temperature_2m_min}."""
    times = daily.get("time", []) if daily else []
    values = daily.get("temperature_2m_min", []) if daily else []
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
                    help="grid resolution in degrees (default 1.5)")
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--end-year", type=int, default=2025)
    ap.add_argument("--batch", type=int, default=100,
                    help="locations per API request")
    ap.add_argument("--sleep", type=float, default=1.0,
                    help="seconds to pause between batch requests")
    args = ap.parse_args()

    end_year = args.end_year
    start_year = end_year - args.years + 1
    start_date, end_date = f"{start_year}-01-01", f"{end_year}-12-31"
    months = month_labels(start_year, end_year)

    cells = land_grid(args.step)
    nbatch = (len(cells) + args.batch - 1) // args.batch
    print(f"fetching {len(cells)} cells x {args.years} yr in {nbatch} batches "
          f"of <= {args.batch} ...", file=sys.stderr)

    session = requests.Session()
    session.headers["User-Agent"] = "CoolSat/urban-heat (open-meteo archive)"

    grid = []
    for bi in range(nbatch):
        batch = cells[bi * args.batch:(bi + 1) * args.batch]
        results = fetch_batch(batch, start_date, end_date, session)
        for (lat, lon), loc in zip(batch, results):
            daily = loc.get("daily") if isinstance(loc, dict) else None
            grid.append({"lat": round(lat, 3), "lon": round(lon, 3),
                         "v": monthly_means(daily, months)})
        print(f"  batch {bi + 1}/{nbatch}  ({len(grid)}/{len(cells)} cells)",
              file=sys.stderr)
        if bi < nbatch - 1:
            time.sleep(args.sleep)

    if len(grid) != len(cells):
        print(f"WARNING: got {len(grid)} cells, expected {len(cells)}",
              file=sys.stderr)

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
