#!/usr/bin/env python3
"""Select an approximate empty plot inside the Skanstull/Hammarby Sluss bbox."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

PROJECT = Path.home() / "projects" / "stockholm-poc"
OUT = PROJECT / "out"
DATA = Path.home() / "gis-data" / "skanstull"
LOG = OUT / "run_log.md"
W, S, E, N = 18.0695, 59.3050, 18.0782, 59.3105


def log(msg: str) -> None:
    print(msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n- {msg}\n")


def parts(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    if geom.geom_type == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(parts(g))
        return out
    return []


def main():
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
    minx, miny = tr.transform(W, S)
    maxx, maxy = tr.transform(E, N)
    site = box(minx, miny, maxx, maxy)

    buildings = gpd.read_file(DATA / "buildings_3006.gpkg").to_crs("EPSG:3006")
    buildings = gpd.clip(buildings, gpd.GeoDataFrame(geometry=[site], crs="EPSG:3006"))
    subtract_geoms = []
    if not buildings.empty:
        subtract_geoms.append(unary_union([g for g in buildings.geometry if g is not None and not g.is_empty]).buffer(2.0))
    try:
        streets = gpd.read_file(DATA / "streets_3006.gpkg").to_crs("EPSG:3006")
        streets = gpd.clip(streets, gpd.GeoDataFrame(geometry=[site], crs="EPSG:3006"))
        if not streets.empty:
            subtract_geoms.append(unary_union([g for g in streets.geometry if g is not None and not g.is_empty]).buffer(7.0))
    except Exception as e:
        log(f"Street buffer skipped while selecting empty plot: {repr(e)}")

    available = site
    if subtract_geoms:
        available = site.difference(unary_union(subtract_geoms))
    available = available.buffer(0)
    candidates = [p.buffer(0) for p in parts(available) if p.area > 120]
    candidates = sorted(candidates, key=lambda p: p.area, reverse=True)

    qualified = [p for p in candidates if 800 <= p.area <= 3000]
    if qualified:
        selected = max(qualified, key=lambda p: p.area)
        rule = "largest polygon in preferred 800–3000 m² range"
    elif candidates:
        selected = candidates[0]
        rule = "largest available polygon because no 800–3000 m² candidate qualified"
    else:
        # Last-resort internal fallback: a 40x40 m plot in the bbox.
        selected = box((minx + maxx) / 2 - 20, (miny + maxy) / 2 - 20, (minx + maxx) / 2 + 20, (miny + maxy) / 2 + 20)
        rule = "synthetic 40x40 m fallback because no empty polygon remained"

    selected = selected.simplify(0.5, preserve_topology=True).buffer(0)
    if selected.geom_type != "Polygon":
        selected = max(parts(selected), key=lambda p: p.area)
    (OUT / "empty_plot.wkt").write_text(selected.wkt, encoding="utf-8")
    c = selected.centroid
    log(f"Selected empty plot area: {selected.area:.1f} m²; centroid EPSG:3006: ({c.x:.2f}, {c.y:.2f}); rule: {rule}")
    print(f"area={selected.area:.1f} centroid=({c.x:.2f},{c.y:.2f}) rule={rule}")


if __name__ == "__main__":
    main()
