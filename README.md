# CoolSat — Urban Heat Mitigation via AI/ML

Geospatial, physics-informed decision support for identifying urban heat-stress
hotspots, quantifying the drivers of urban heating, and generating optimized,
scenario-based cooling interventions.

This repository is being built up incrementally toward that full framework
(heat-stress mapping → driver attribution → physics-informed ML → cooling-scenario
optimization). **This first milestone** delivers the baseline heat-observation
layer: an interactive map of **average monthly night-time temperature across the
Continental US over the last 10 years (2016–2025)**, driven by a timeline slider.

Night-time temperature is the metric that matters most for urban heat stress — the
urban-heat-island signal is strongest overnight, when built surfaces re-radiate the
day's stored heat and cities fail to cool down.

## The visualization

`index.html` (repo root) — a self-contained, theme-aware viewer:

- Diverging blue↔red heat map of the CONUS, one colored cell per grid point.
- A **timeline slider + play button** sweeping all 120 months (2016-01 → 2025-12).
- Live stat tiles: national mean night-time temperature, hottest/coolest cell, and
  the decadal anomaly vs the same month in the base year (surfaces the warming trend).
- Hover any cell for its temperature and location.

It is served at the site root, so it deploys as a plain static site on Vercel (or
any static host) with no build step. Open `index.html` directly once a data file
exists at `viz/data/us_nighttime_monthly.json`.

## Data

**Metric.** "Night-time temperature" is the monthly mean of the **daily-minimum
2 m air temperature** (`temperature_2m_min`) — the diurnal minimum occurs shortly
before dawn, so it is the standard proxy for night-time / urban-heat-island studies.

**Source.** [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
(ERA5 reanalysis) — free, no API key. A regular lat/lon grid is sampled across the
CONUS and clipped to a simplified US boundary polygon.

### Generate the data

```bash
# Real Open-Meteo data (run where archive-api.open-meteo.com is reachable):
pip install requests
python data/fetch_openmeteo.py                # 2.5° grid (~130 cells), 10 yrs
python data/fetch_openmeteo.py --step 2.0     # finer, but see the quota note below

# Offline demo climatology (no network — used to develop/preview the viz):
python data/gen_demo_data.py
```

Both scripts write the **same JSON schema** to `viz/data/us_nighttime_monthly.json`,
so the viewer works identically with either. The committed data file is the
**demo climatology** (a deterministic model of latitude, elevation/continentality,
seasonal cycle, decadal warming, and urban-heat offsets) — it is realistic in shape
but is *not* observations. The viewer shows a clear `DEMO` badge until you swap in
real data. Re-run `fetch_openmeteo.py` to replace it.

> ℹ️ **How the committed data is produced.** The Open-Meteo host is blocked from the
> build container's network, so the real fetch runs on a **GitHub-hosted runner**
> (`.github/workflows/fetch-openmeteo.yml`), which commits the static JSON back to
> the branch. Open-Meteo's free tier caps roughly **200 cells × 10 yr per hour per
> IP**, so a single run must stay under that — the default **2.5° grid (~130 cells)**
> completes in one pass. A finer grid needs a paid API key or several runs spread
> across hours (each pass only overwrites on success, so the map is never left with
> holes). Trigger a refresh from the repo's **Actions → Fetch Open-Meteo night-time
> data → Run workflow**, or by pushing a change to the fetch script.

## Layout

```
index.html             # interactive slider map (self-contained, served at site root)
vercel.json            # static-hosting config (clean URLs, cache headers)
data/
  us_region.py         # CONUS boundary polygon, sampling grid, city list (shared)
  fetch_openmeteo.py   # pull real night-time temps from Open-Meteo (ERA5)
  gen_demo_data.py     # offline synthetic climatology (same schema)
viz/
  data/
    us_nighttime_monthly.json   # generated grid data
```

## Roadmap

- [x] Baseline night-time heat layer + timeline slider (this milestone)
- [ ] Landsat 8 / ECOSTRESS land-surface-temperature hotspots
- [ ] Driver attribution (LULC, NDVI/NDBI, urban morphology, ERA5 atmospherics)
- [ ] Physics-informed ML for LST ↔ driver relationships
- [ ] Cooling-scenario simulation & optimization (greening, cool roofs, albedo, water)
