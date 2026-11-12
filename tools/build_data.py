#!/usr/bin/env python3
"""Rebuild docs/data/*.geojson from their upstream sources.

HUC8 subbasins come from the USGS Watershed Boundary Dataset (layer 4 of the
WBD MapServer); state outlines from the Census TIGER cartographic boundaries.

Both are simplified with mapshaper (via npx) rather than by the ArcGIS service,
because the service generalizes each polygon independently and that tears shared
watershed borders into gaps and slivers. mapshaper simplifies the shared edge
once, so adjacent basins stay welded.

Usage:  python3 tools/build_data.py
Needs:  node/npx on PATH.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data"

WBD = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query"
TIGER = "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_state_20m.zip"

# Server-side generalization tolerance in degrees. Coarse enough to keep the
# download reasonable, fine enough that mapshaper still has detail to work with.
OFFSET = "0.005"
PAGE = 1000
HUC8_RETAIN = "15%"   # ~3.1 MB raw, ~0.9 MB gzipped over the wire
STATE_RETAIN = "40%"


def npx(*args):
    subprocess.run(["npx", "-y", "mapshaper@0.6", *args], check=True)


def fetch_huc8(dest):
    feats, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "where": "1=1",
            "outFields": "huc8,name,areasqkm,states",
            "returnGeometry": "true",
            "maxAllowableOffset": OFFSET,
            "geometryPrecision": "4",
            "outSR": "4326",
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
        })
        with urllib.request.urlopen(f"{WBD}?{q}", timeout=180) as r:
            got = json.load(r).get("features", [])
        if not got:
            break
        feats.extend(got)
        print(f"  HUC8 {len(feats)}", flush=True)
        if len(got) < PAGE:
            break
        offset += PAGE
    dest.write_text(json.dumps(
        {"type": "FeatureCollection", "features": feats}, separators=(",", ":")))
    return len(feats)


def fetch_states(tmp):
    zpath = tmp / "states.zip"
    with urllib.request.urlopen(TIGER, timeout=180) as r, open(zpath, "wb") as f:
        shutil.copyfileobj(r, f)
    with zipfile.ZipFile(zpath) as z:
        z.extractall(tmp)
    return tmp / "cb_2022_us_state_20m.shp"


def main():
    if not shutil.which("npx"):
        sys.exit("npx not found - install Node.js first")
    OUT.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)

        raw = tmp / "huc8_raw.geojson"
        n = fetch_huc8(raw)
        npx(str(raw), "-simplify", f"percentage={HUC8_RETAIN}", "keep-shapes",
            "-o", "precision=0.0001", "format=geojson", str(OUT / "huc8.geojson"))
        print(f"wrote docs/data/huc8.geojson ({n} subbasins)")

        shp = fetch_states(tmp)
        npx(str(shp), "-proj", "wgs84", "-filter-fields", "NAME,STUSPS",
            "-simplify", f"percentage={STATE_RETAIN}", "keep-shapes",
            "-o", "precision=0.0001", "format=geojson", str(OUT / "states.geojson"))
        print("wrote docs/data/states.geojson")


if __name__ == "__main__":
    main()
