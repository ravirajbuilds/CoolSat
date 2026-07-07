"""Shared geography for the CoolSat US night-time heat visualization.

Defines a simplified Continental US (CONUS) boundary polygon, a regular
lat/lon sampling grid clipped to that polygon, and a set of major cities.
Both the live Open-Meteo fetcher (`fetch_openmeteo.py`) and the offline demo
generator (`gen_demo_data.py`) import from here so they emit the *same* grid.
"""

# Simplified CONUS boundary, traced clockwise (lon, lat). ~45 vertices — coarse
# but recognizably the US, and good enough to mask ocean cells out of the grid.
CONUS_POLYGON = [
    (-124.7, 48.4), (-123.0, 49.0), (-104.0, 49.0), (-95.2, 49.0),
    (-90.0, 48.1), (-84.5, 46.5), (-82.5, 45.0), (-83.1, 41.9),
    (-79.0, 43.3), (-76.5, 43.6), (-73.3, 45.0), (-71.1, 45.3),
    (-69.2, 47.4), (-67.2, 45.7), (-70.0, 43.5), (-70.8, 42.3),
    (-71.5, 41.3), (-74.0, 40.5), (-75.5, 38.5), (-76.0, 37.0),
    (-75.7, 35.2), (-78.6, 33.9), (-80.9, 32.0), (-81.4, 30.7),
    (-80.1, 25.2), (-81.1, 24.6), (-82.8, 27.8), (-84.0, 30.1),
    (-88.0, 30.3), (-90.2, 29.1), (-93.8, 29.7), (-97.2, 27.8),
    (-99.5, 27.5), (-101.0, 29.5), (-103.0, 29.0), (-106.5, 31.8),
    (-111.0, 31.3), (-114.7, 32.5), (-117.1, 32.5), (-120.5, 34.5),
    (-122.0, 37.0), (-124.0, 40.4), (-124.2, 43.0), (-124.5, 46.0),
    (-124.7, 48.4),
]

# Major US cities carrying a nominal urban-heat-island offset (used only by the
# demo generator; the live fetcher samples each city as an ordinary grid point).
CITIES = [
    ("New York",      40.71, -74.01, 2.5),
    ("Los Angeles",   34.05, -118.24, 3.0),
    ("Chicago",       41.88, -87.63, 2.2),
    ("Houston",       29.76, -95.37, 2.6),
    ("Phoenix",       33.45, -112.07, 3.6),
    ("Dallas",        32.78, -96.80, 2.4),
    ("Miami",         25.76, -80.19, 2.0),
    ("Atlanta",       33.75, -84.39, 2.2),
    ("Seattle",       47.61, -122.33, 1.7),
    ("Denver",        39.74, -104.99, 2.0),
    ("Minneapolis",   44.98, -93.27, 2.0),
    ("Boston",        42.36, -71.06, 2.0),
    ("San Francisco", 37.77, -122.42, 1.8),
    ("Las Vegas",     36.17, -115.14, 3.3),
    ("Detroit",       42.33, -83.05, 2.0),
    ("Washington DC", 38.90, -77.04, 2.3),
    ("Kansas City",   39.10, -94.58, 1.8),
    ("Salt Lake City",40.76, -111.89, 1.8),
    ("New Orleans",   29.95, -90.07, 2.0),
    ("Portland",      45.52, -122.68, 1.7),
]

# Sampling grid extent (CONUS bounding box) and resolution in degrees.
LON_MIN, LON_MAX = -125.0, -66.5
LAT_MIN, LAT_MAX = 24.5, 49.5
GRID_STEP = 0.8


def _point_in_polygon(lon, lat, poly):
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def _frange(start, stop, step):
    vals = []
    v = start
    # guard against float drift
    while v <= stop + 1e-9:
        vals.append(round(v, 4))
        v += step
    return vals


def land_grid():
    """Return (lons, lats, cells) where cells is a list of (lat, lon) points
    inside the CONUS polygon, on the regular grid."""
    lons = _frange(LON_MIN, LON_MAX, GRID_STEP)
    lats = _frange(LAT_MIN, LAT_MAX, GRID_STEP)
    cells = []
    for lat in lats:
        for lon in lons:
            if _point_in_polygon(lon, lat, CONUS_POLYGON):
                cells.append((lat, lon))
    return lons, lats, cells


def month_labels(start_year, end_year):
    """['YYYY-MM', ...] inclusive of both years, Jan..Dec."""
    out = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            out.append(f"{y}-{m:02d}")
    return out


if __name__ == "__main__":
    lons, lats, cells = land_grid()
    print(f"grid: {len(lons)} lon x {len(lats)} lat = {len(lons)*len(lats)} cells")
    print(f"land cells inside CONUS polygon: {len(cells)}")
