#!/usr/bin/env python3
"""Rebuild docs/data/*.geojson from their upstream sources.

HUC8 subbasins come from the USGS Watershed Boundary Dataset (layer 4 of the
WBD MapServer); state outlines from the Census TIGER cartographic boundaries;
flood events from the NOAA NCEI Storm Events Database.

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
import csv
import gzip
import io
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data"

WBD = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query"
TIGER = "https://www2.census.gov/geo/tiger/GENZ2022/shp/cb_2022_us_state_20m.zip"
STORM = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
FLOOD_YEAR = 2026
FLOOD_TYPES = {"Flood", "Flash Flood", "Coastal Flood", "Lakeshore Flood"}

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


def _money(s):
    """'1.50M' -> 1500000.0. Blank and unparseable both mean zero."""
    s = (s or "").strip()
    if not s:
        return 0.0
    mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
    try:
        return float(s[:-1]) * mult[s[-1].upper()] if s[-1].upper() in mult else float(s)
    except ValueError:
        return 0.0


def _clip(s, n):
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "\u2026"


def build_floods(dest):
    """Flood events for FLOOD_YEAR, as points where each one began.

    NCEI stamps each file with its compile date, so the newest one for the year
    has to be discovered rather than hardcoded. The database runs about three
    months behind, so a year in progress stops short of today.
    """
    with urllib.request.urlopen(STORM, timeout=120) as r:
        listing = r.read().decode("utf-8", "replace")
    names = re.findall(rf"StormEvents_details-ftp_v1\.0_d{FLOOD_YEAR}_c\d+\.csv\.gz", listing)
    if not names:
        print(f"  no storm-events file published for {FLOOD_YEAR} yet - skipping floods")
        return 0
    newest = sorted(set(names))[-1]
    print(f"  storm events: {newest}")

    with urllib.request.urlopen(STORM + newest, timeout=600) as r:
        raw = gzip.decompress(r.read()).decode("utf-8", "replace")

    csv.field_size_limit(10 ** 9)
    feats = []
    for row in csv.DictReader(io.StringIO(raw)):
        if row["EVENT_TYPE"] not in FLOOD_TYPES:
            continue
        try:
            lat, lon = float(row["BEGIN_LAT"]), float(row["BEGIN_LON"])
        except (TypeError, ValueError):
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue
        deaths = int(row["DEATHS_DIRECT"] or 0) + int(row["DEATHS_INDIRECT"] or 0)
        inj = int(row["INJURIES_DIRECT"] or 0) + int(row["INJURIES_INDIRECT"] or 0)
        dmg = _money(row["DAMAGE_PROPERTY"]) + _money(row["DAMAGE_CROPS"])
        major = bool(deaths or inj or dmg >= 1e5)
        props = {
            "id": int(row["EVENT_ID"]),
            "type": row["EVENT_TYPE"],
            "st": row["STATE"].title(),
            "cz": row["CZ_NAME"].title(),
            "beg": row["BEGIN_DATE_TIME"],
            "end": row["END_DATE_TIME"],
            "tz": row["CZ_TIMEZONE"],
            "d": deaths,
            "i": inj,
            "dmg": round(dmg),
            "sev": "major" if major else ("moderate" if dmg >= 1e4 else "minor"),
        }
        if row["FLOOD_CAUSE"]:
            props["cause"] = row["FLOOD_CAUSE"]
        if row["SOURCE"]:
            props["src"] = row["SOURCE"]
        if row["BEGIN_LOCATION"]:
            props["near"] = " ".join(x for x in (row["BEGIN_RANGE"], row["BEGIN_AZIMUTH"],
                                                 row["BEGIN_LOCATION"].title()) if x)
        note = _clip(row["EVENT_NARRATIVE"], 600)
        if note:
            props["note"] = note
        # The episode narrative covers the whole weather system and repeats across
        # its events - carry it only where the detail earns the bytes.
        if major:
            epi = _clip(row["EPISODE_NARRATIVE"], 900)
            if epi:
                props["epi"] = epi
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [round(lon, 4), round(lat, 4)]},
                      "properties": props})

    # Worst last, so the gravest events draw on top of the crowd.
    feats.sort(key=lambda f: (f["properties"]["d"], f["properties"]["dmg"]))
    dest.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                               separators=(",", ":"), ensure_ascii=False))
    return len(feats)


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

        n = build_floods(OUT / "floods.geojson")
        if n:
            print(f"wrote docs/data/floods.geojson ({n} flood events)")

        shp = fetch_states(tmp)
        npx(str(shp), "-proj", "wgs84", "-filter-fields", "NAME,STUSPS",
            "-simplify", f"percentage={STATE_RETAIN}", "keep-shapes",
            "-o", "precision=0.0001", "format=geojson", str(OUT / "states.geojson"))
        print("wrote docs/data/states.geojson")


if __name__ == "__main__":
    main()
