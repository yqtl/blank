# Ljustergränd Urban Massing POC Demo

This demo builds a self-contained local pipeline for a conceptual LLM-driven urban massing workflow at Ljustergränd 5, 116 68 Stockholm, Stockholm. It fetches or synthesizes OSM context, works in EPSG:3006 / SWEREF 99 TM, selects an approximate empty plot, generates five parametric massing variants, exports GLB models, renders PNG images, and writes a report.

## Required system packages

Ubuntu baseline:

```bash
sudo apt update
sudo apt install -y build-essential git curl wget python3-pip python3-venv pipx gdal-bin python3-gdal libgdal-dev proj-bin libproj-dev nodejs npm libxfixes3 libxi6 libxrender1 libxrandr2 libxcursor1 libxinerama1 libxxf86vm1 libgl1 libegl1 libsm6 libice6 libfontconfig1 libxkbcommon0
```

QGIS 3.40 LTR is preferred for site preview if available, but the script falls back to GeoPandas/Matplotlib. Blender 4.5 LTS is preferred; a portable Linux tarball works.

## Setup

```bash
cd ~/projects/ljustergrand-poc
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install 'osmnx>=2.1' geopandas rasterio pyproj momepy shapely fiona matplotlib
```

## Run

```bash
cd ~/projects/ljustergrand-poc
source .venv/bin/activate
python fetch_data.py
python create_qgis_preview.py
python find_empty_plot.py
./blender/blender --background --python create_blender_demo.py
```

This workspace includes a downloaded portable Blender 4.5 LTS binary at `./blender/blender`. If a system Blender 4.5 is on PATH, `blender --background --python create_blender_demo.py` also works.

## Expected outputs

- `out/qgis_site.png` — GIS/site preview
- `out/empty_plot.wkt` — selected empty plot geometry in EPSG:3006
- `out/V1.glb` through `out/V5.glb` — variant GLB exports
- `out/V1.png` through `out/V5.png` — rendered demo images
- `out/report.md` — report with FAR/GFA metrics
- `out/run_log.md` — execution log and fallbacks

## Troubleshooting

- If Overpass rate-limits or fails twice, `fetch_data.py` writes a small synthetic EPSG:3006 fallback dataset so the visual demo still runs.
- If QGIS Python bindings are unavailable, `create_qgis_preview.py` logs the fallback and renders via GeoPandas/Matplotlib.
- If Blender lacks Python GIS packages, `create_blender_demo.py` uses the project virtual environment to prepare simplified scene JSON, then builds meshes directly with Blender Python.
- No generated building element exceeds 60 m.
