# Run log

Started: 2026-04-24T20:05:59+00:00
Site: Ljustergränd 5, 116 68 Stockholm
Source: copied/adapted from stockholm-poc

## Python dependency install
- Completed: 2026-04-24T20:07:33+00:00
- osmnx 2.1.0
- geopandas 1.1.3
- rasterio 1.5.0
- pyproj 3.7.2
- shapely 2.1.2
- fiona 1.10.1

- Fetching OSM buildings and street network with OSMnx for bbox W,S,E,N (18.0764, 59.3004, 18.0895, 59.3094)

## Fetch data failure and fix
- Command: python fetch_data.py
- Error: pyogrio.errors.FieldError: Error adding field 'HEIGHT' to layer
- Fix attempt: renamed case-insensitive OSM height tag before deriving HEIGHT.

- Fetching OSM buildings and street network with OSMnx for bbox W,S,E,N (18.0764, 59.3004, 18.0895, 59.3094)

- Saved buildings to /home/vscode/gis-data/ljustergrand/buildings_3006.gpkg

- Saved streets to /home/vscode/gis-data/ljustergrand/streets_3006.gpkg

- Building count: 262; mean HEIGHT: 14.77 m

- QGIS renderer unavailable/failed: ModuleNotFoundError("No module named 'qgis'")

- Rendered out/qgis_site.png with GeoPandas/Matplotlib fallback (QGIS Python unavailable).

- Selected empty plot area: 2738.7 m²; centroid EPSG:3006: (675687.64, 6578405.58); rule: largest polygon in preferred 800–3000 m² range

- Preparing scene data with command: /home/vscode/projects/ljustergrand-poc/.venv/bin/python /home/vscode/projects/ljustergrand-poc/_prepare_scene_data.py

- Prepared Blender scene data: 245 context building parts; plot area 2738.7 m²

- Rendered out/V1.png

- Exported out/V1.glb

- Rendered out/V2.png

- Exported out/V2.glb

- Rendered out/V3.png

- Exported out/V3.glb

- Rendered out/V4.png

- Exported out/V4.glb

- Rendered out/V5.png

- Exported out/V5.glb

- Wrote out/report.md

- Blender demo complete.
