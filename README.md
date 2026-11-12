# HUC8 Watershed Explorer

An interactive map of the 2,456 HUC8 subbasins of the USGS Watershed Boundary
Dataset, with 2026 US flood events on top, over a switchable basemap. Hover any
basin for its name, HUC8 code, area and states; click a flood point for its full
report.

Live: https://theonlyrealagentp.github.io/CCE114-WebMap/

## What it does

- **Hover + pin.** Moving over a basin highlights it and fills the side panel;
  clicking pins it so the details stay put.
- **Flood events.** 3,971 NOAA-recorded floods, sized by severity. Clicking one
  gives the full report: dates, location, deaths, injuries, damage, flood cause,
  reporting source, and the forecaster's written account of what happened.
- **11 basemaps.** OpenFreeMap (Positron, Bright, Liberty), Carto (Voyager, Dark
  Matter), Esri (Imagery, Topographic, Streets), USGS (Imagery, Topo),
  OpenTopoMap and OpenStreetMap. Overlay colors re-step for dark basemaps.
- **Color by area** using a sequential ramp, with breaks set on the actual
  percentile distribution so the handful of very large basins don't flatten
  everything else.
- **Filter by region** (the 22 HUC2 regions) and **search** by name or HUC8 code.
- **Layer toggles** for watershed lines, basin fill, and state boundaries.

## Layout

- `docs/` — the published site (GitHub Pages serves this folder).
  - `index.html` — the whole app; no build step, no dependencies beyond the
    MapLibre GL CDN.
  - `data/huc8.geojson` — 2,456 subbasins, simplified (~3.1 MB, ~0.9 MB gzipped).
  - `data/states.geojson` — state outlines from Census TIGER 1:20m.
  - `data/floods.geojson` — 2026 flood events (~1.9 MB, ~360 KB gzipped).
- `tools/build_data.py` — rebuilds both GeoJSON files from their upstream sources.
- `serve.sh` — serves `docs/` locally and opens it.

## Running it locally

```sh
./serve.sh            # http://localhost:8000
```

## Rebuilding the data

```sh
python3 tools/build_data.py    # needs node/npx for mapshaper
```

Simplification is done by mapshaper rather than by the ArcGIS service, because
the service generalizes each polygon on its own and that tears shared watershed
borders into gaps and slivers. mapshaper simplifies each shared edge once, so
neighboring basins stay welded.

## Flood data coverage

**1 January – 31 July 2026.** NOAA publishes the Storm Events Database on roughly
a three-month lag, so the rest of 2026 is not available yet. Re-running
`tools/build_data.py` later picks up whatever has been published since; the
script finds the newest file for the year on its own.

That window holds 3,971 flood events with coordinates — 3,028 flash floods and
943 floods — carrying 39 deaths and about $1.4 billion in reported damage.
"Major" means the event killed someone, injured someone, or caused at least
$100k in damage; 155 qualify.

Damage figures are the reporting Weather Forecast Office's estimate at the time,
not an audited loss, and a point marks where the event *began* rather than its
full extent.

## Notes on the data

- The outlines are **simplified for display**. Use the USGS source data for any
  analysis or area calculation.
- Eleven transboundary basins (Columbia and Great Lakes headwaters reaching into
  Canada) have no reported area, since WBD only measures the US portion. They
  render in neutral gray and the panel says so rather than showing a false zero.

## Why there's no Google basemap

Google's tiles require the Maps Tiles API with a billing-enabled key. A static
site can't hold that key without exposing it publicly, and the undocumented
`mt*.google.com` tile endpoints are a Terms of Service violation. Esri World
Imagery and USGS Imagery cover the same need, free and keyless.

## Sources

- [USGS Watershed Boundary Dataset](https://www.usgs.gov/national-hydrography/watershed-boundary-dataset) (public domain)
- [US Census TIGER cartographic boundaries](https://www.census.gov/geographies/mapping-files/time-series/geo/cartographic-boundary.html) (public domain)
- [NOAA NCEI Storm Events Database](https://www.ncei.noaa.gov/products/storm-events-database) (public domain)
- Basemaps as attributed in the map's attribution control.

## License

MIT — see [LICENSE](LICENSE).
