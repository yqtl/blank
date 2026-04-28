# Stockholm Urban Massing POC — Ljustergränd 5 / Hammarbyhöjden-Skanstull edge

## Site description
Conceptual one-day massing demo for Ljustergränd 5, 116 68 Stockholm, near the Hammarby/Södermalm edge. Work is in EPSG:3006 / SWEREF 99 TM using a local WGS84 bbox around geocoded Ljustergränd 5: 18.0764,59.3004,18.0895,59.3094.

## Data sources used
- OpenStreetMap building footprints and street network via OSMnx/Overpass, projected to EPSG:3006.
- Empty plot derived by subtracting building footprints and buffered street geometry from the site bbox.

## Empty plot
- Area: 2738.7 m²
- Centroid EPSG:3006: (675687.64, 6578405.58)

## Variant metrics

| Variant | Type | Plot area m² | Footprint area m² | Floors | Max height m | Target FAR | GFA m² | Realised FAR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| V1 | courtyard perimeter block | 2738.7 | 912.5 | 6 | 18.0 | 2.0 | 5474.9 | 2.00 |
| V2 | L-shape with stepped roof | 2738.7 | 1600.9 | 6 | 18.0 | 3.5 | 8334.8 | 3.04 |
| V3 | tower plus podium | 2738.7 | 811.8 | 20 | 60.0 | 5.0 | 13564.4 | 4.95 |
| V4 | twin parallel slabs | 2738.7 | 1069.7 | 11 | 33.0 | 4.2 | 11766.0 | 4.30 |
| V5 | compact terraced block | 2738.7 | 961.4 | 8 | 24.0 | 2.8 | 7633.6 | 2.79 |

## Limitations
- OSM building heights are approximate: `building:levels × 3 m`, otherwise 12 m fallback.
- DEM/terrain was omitted unless already available; this POC uses flat EPSG:3006 geometry.
- Massing is conceptual and not a planning-compliant architectural proposal.
- FAR is approximate due to simplified geometry and conceptual stepped/tower volumes.
- Rendered with Blender 4.5.3 LTS using BLENDER_WORKBENCH; QGIS preview may use Matplotlib fallback if QGIS Python is unavailable.

## Reproduce
```bash
cd ~/projects/ljustergrand-poc
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install 'osmnx>=2.1' geopandas rasterio pyproj momepy shapely fiona matplotlib
python fetch_data.py
python create_qgis_preview.py
python find_empty_plot.py
./blender/blender --background --python create_blender_demo.py
```
