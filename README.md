# HUC8 Watershed Explorer

An interactive map of the 2,456 HUC8 subbasins of the USGS Watershed Boundary
Dataset, drawn over a switchable basemap. Hover any basin for its name, HUC8
code, area and states; click to pin it.

Live: https://theonlyrealagentp.github.io/CCE114-WebMap/

## What it does

- **Hover + pin.** Moving over a basin highlights it and fills the side panel;
  clicking pins it so the details stay put.
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
- Basemaps as attributed in the map's attribution control.

## License

MIT — see [LICENSE](LICENSE).
