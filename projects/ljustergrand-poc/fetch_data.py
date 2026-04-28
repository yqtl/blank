#!/usr/bin/env python3
"""Fetch or synthesize OSM data for Ljustergränd 5 in EPSG:3006."""
from __future__ import annotations

import inspect
import math
import sys
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box

PROJECT = Path.home() / "projects" / "ljustergrand-poc"
OUT = PROJECT / "out"
DATA = Path.home() / "gis-data" / "ljustergrand"
LOG = OUT / "run_log.md"
W, S, E, N = 18.0764, 59.3004, 18.0895, 59.3094
CRS_WGS = "EPSG:4326"
CRS_WORK = "EPSG:3006"

OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n- {msg}\n")


def parse_levels(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().split(";")[0].split(",")[0]
    try:
        return float(s)
    except Exception:
        return None


def synth_data(reason: str):
    log(f"Using synthetic fallback dataset in EPSG:3006 because OSM fetch failed: {reason}")
    tr = Transformer.from_crs(CRS_WGS, CRS_WORK, always_xy=True)
    minx, miny = tr.transform(W, S)
    maxx, maxy = tr.transform(E, N)
    site = box(minx, miny, maxx, maxy)

    # Leave a central/southern rectangular plot open for selection.
    open_plot = box(minx + 210, miny + 210, minx + 260, miny + 260)
    polys, levels = [], []
    x = minx + 20
    i = 0
    while x < maxx - 35:
        y = miny + 20
        while y < maxy - 35:
            b = box(x, y, x + 22, y + 18)
            if site.contains(b) and not b.intersects(open_plot.buffer(25)) and (i % 5 != 0):
                polys.append(b)
                levels.append([3, 4, 5, 6, 7][i % 5])
            y += 62
            i += 1
        x += 70
    buildings = gpd.GeoDataFrame(
        {"building": ["yes"] * len(polys), "building:levels": levels}, geometry=polys, crs=CRS_WORK
    )
    buildings["HEIGHT"] = buildings["building:levels"].astype(float) * 3.0

    lines = []
    for x in [minx + d for d in range(0, int(maxx - minx) + 1, 70)]:
        lines.append(LineString([(x, miny), (x, maxy)]))
    for y in [miny + d for d in range(0, int(maxy - miny) + 1, 70)]:
        lines.append(LineString([(minx, y), (maxx, y)]))
    streets = gpd.GeoDataFrame({"highway": ["residential"] * len(lines)}, geometry=lines, crs=CRS_WORK)
    return buildings, streets, True


def call_osmnx():
    import osmnx as ox

    tags = {"building": True}
    bbox_wsen = (W, S, E, N)

    def features():
        sig = inspect.signature(ox.features_from_bbox)
        # OSMnx >=2.0 accepts bbox tuple, older accepted north/south/east/west positional args.
        if "bbox" in sig.parameters:
            return ox.features_from_bbox(bbox_wsen, tags=tags)
        return ox.features_from_bbox(N, S, E, W, tags=tags)

    def graph():
        sig = inspect.signature(ox.graph_from_bbox)
        if "bbox" in sig.parameters:
            return ox.graph_from_bbox(bbox_wsen, network_type="drive")
        return ox.graph_from_bbox(N, S, E, W, network_type="drive")

    log("Fetching OSM buildings and street network with OSMnx for bbox W,S,E,N " + str(bbox_wsen))
    b = features()
    if b.empty:
        raise RuntimeError("OSM building query returned no features")
    b = b[b.geometry.notna()].copy()
    b = b[b.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    b = b.reset_index(drop=True)
    G = graph()
    _, edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
    edges = edges.reset_index(drop=True)

    b3006 = b.to_crs(CRS_WORK)
    s3006 = edges.to_crs(CRS_WORK)
    return b3006, s3006, False


def main():
    fallback = False
    last_err = None
    for attempt in [1, 2]:
        try:
            buildings, streets, fallback = call_osmnx()
            break
        except Exception as e:  # rate-limit/network/schema safe path
            last_err = repr(e)
            log(f"OSM fetch attempt {attempt} failed: {last_err}")
            if attempt == 1:
                time.sleep(20)
            else:
                buildings, streets, fallback = synth_data(last_err)

    # GeoPackage/OGR treats field names case-insensitively, so an OSM `height`
    # tag can collide with our derived `HEIGHT` column. Preserve it under a
    # distinct name before writing.
    for col in list(buildings.columns):
        if col != "geometry" and col.lower() == "height":
            buildings = buildings.rename(columns={col: "osm_height_tag"})
    if "HEIGHT" in buildings.columns:
        buildings = buildings.drop(columns=["HEIGHT"])

    if "building:levels" in buildings.columns:
        levels = buildings["building:levels"].apply(parse_levels)
        buildings["HEIGHT"] = levels.apply(lambda x: x * 3.0 if x and x > 0 else 12.0)
    elif "levels" in buildings.columns:
        levels = buildings["levels"].apply(parse_levels)
        buildings["HEIGHT"] = levels.apply(lambda x: x * 3.0 if x and x > 0 else 12.0)
    else:
        buildings["HEIGHT"] = 12.0
    buildings["HEIGHT"] = buildings["HEIGHT"].clip(lower=3.0, upper=80.0)

    # Keep serializable/simple attributes for GPKG stability.
    for gdf in (buildings, streets):
        for col in list(gdf.columns):
            if col == "geometry":
                continue
            if gdf[col].map(lambda x: isinstance(x, (list, dict, tuple, set))).any():
                gdf[col] = gdf[col].astype(str)

    bpath = DATA / "buildings_3006.gpkg"
    spath = DATA / "streets_3006.gpkg"
    buildings.to_file(bpath, layer="buildings", driver="GPKG")
    streets.to_file(spath, layer="streets", driver="GPKG")
    (DATA / "fallback_used.txt").write_text("yes\n" if fallback else "no\n", encoding="utf-8")

    log(f"Saved buildings to {bpath}")
    log(f"Saved streets to {spath}")
    log(f"Building count: {len(buildings)}; mean HEIGHT: {buildings['HEIGHT'].mean():.2f} m")
    print(f"building_count={len(buildings)} mean_height={buildings['HEIGHT'].mean():.2f} fallback={fallback}")


if __name__ == "__main__":
    main()
