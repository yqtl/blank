# Stockholm Urban Massing POC — Skanstull / Hammarby Sluss

## Site description
Conceptual one-day massing demo for Skanstull / Hammarby Sluss, southern Södermalm, Stockholm. Work is in EPSG:3006 / SWEREF 99 TM using the requested WGS84 bbox 18.0695,59.3050,18.0782,59.3105.

## Data sources used
- OpenStreetMap building footprints and street network via OSMnx/Overpass, projected to EPSG:3006.
- Empty plot derived by subtracting building footprints and buffered street geometry from the site bbox.

## Empty plot
- Area: 2487.4 m²
- Centroid EPSG:3006: (674821.66, 6578236.20)

## Variant metrics

| Variant | Type | Plot area m² | Footprint area m² | Floors | Max height m | Target FAR | GFA m² | Realised FAR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| V1 | courtyard perimeter block | 2487.4 | 827.1 | 6 | 18.0 | 2.0 | 4962.4 | 2.00 |
| V2 | L-shape with stepped roof | 2487.4 | 1274.1 | 7 | 21.0 | 3.5 | 8480.6 | 3.41 |
| V3 | tower plus podium | 2487.4 | 616.1 | 20 | 60.0 | 5.0 | 10879.5 | 4.37 |

## Limitations
- OSM building heights are approximate: `building:levels × 3 m`, otherwise 12 m fallback.
- DEM/terrain was omitted unless already available; this POC uses flat EPSG:3006 geometry.
- Massing is conceptual and not a planning-compliant architectural proposal.
- FAR is approximate due to simplified geometry and conceptual stepped/tower volumes.
- Rendered with Blender 4.5.3 LTS using BLENDER_WORKBENCH; QGIS preview may use Matplotlib fallback if QGIS Python is unavailable.

## Reproduce
```bash
cd ~/projects/stockholm-poc
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install 'osmnx>=2.1' geopandas rasterio pyproj momepy shapely fiona matplotlib
python fetch_data.py
python create_qgis_preview.py
python find_empty_plot.py
./blender/blender --background --python create_blender_demo.py
```
