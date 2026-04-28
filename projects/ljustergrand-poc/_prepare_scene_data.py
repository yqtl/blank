#!/usr/bin/env python3
"""Prepare simplified EPSG:3006 geometry and variant metrics for Blender."""
from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
from pyproj import Transformer
from shapely import affinity
from shapely.geometry import box, mapping
from shapely.ops import unary_union
from shapely import wkt

PROJECT = Path.home() / "projects" / "ljustergrand-poc"
OUT = PROJECT / "out"
DATA = Path.home() / "gis-data" / "ljustergrand"
LOG = OUT / "run_log.md"
W, S, E, N = 18.0764, 59.3004, 18.0895, 59.3094

VARIANT_SPECS = {
    "V1": {"name": "V1_lowrise", "target_far": 2.0, "max_height": 18.0, "floor_height": 3.0, "setback": 3.0, "type": "courtyard perimeter block"},
    "V2": {"name": "V2_midrise", "target_far": 3.5, "max_height": 32.0, "floor_height": 3.0, "setback": 2.0, "type": "L-shape with stepped roof"},
    "V3": {"name": "V3_tower", "target_far": 5.0, "max_height": 60.0, "floor_height": 3.0, "setback": 4.0, "type": "tower plus podium"},
    "V4": {"name": "V4_twin_slabs", "target_far": 4.2, "max_height": 42.0, "floor_height": 3.0, "setback": 3.5, "type": "twin parallel slabs"},
    "V5": {"name": "V5_terraced_block", "target_far": 2.8, "max_height": 24.0, "floor_height": 3.0, "setback": 1.5, "type": "compact terraced block"},
}


def log(msg: str) -> None:
    print(msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n- {msg}\n")


def polygons(geom):
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    if geom.geom_type == "MultiPolygon":
        return list(geom.geoms)
    if geom.geom_type == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(polygons(g))
        return out
    return []


def clean_polys(geom, min_area=8.0, simplify=0.2):
    out = []
    for p in polygons(geom):
        p = p.buffer(0)
        if simplify:
            p = p.simplify(simplify, preserve_topology=True).buffer(0)
        for q in polygons(p):
            if q.area >= min_area and len(q.exterior.coords) >= 4:
                out.append(q)
    return out


def coords(poly):
    c = list(poly.exterior.coords)
    if len(c) > 160:
        poly = poly.simplify(0.8, preserve_topology=True)
        c = list(poly.exterior.coords)
    return [[round(x, 3), round(y, 3)] for x, y in c]


def inward(plot, setback):
    inner = plot.buffer(-setback).buffer(0)
    if inner.is_empty:
        inner = plot.buffer(-max(0.5, setback * 0.35)).buffer(0)
    if inner.is_empty:
        return plot
    if inner.geom_type != "Polygon":
        inner = max(polygons(inner), key=lambda p: p.area)
    return inner


def scale_to_area(poly, area):
    if poly.area <= 0 or area >= poly.area:
        return poly
    factor = math.sqrt(max(area, 1.0) / poly.area)
    c = poly.centroid
    g = affinity.scale(poly, xfact=factor, yfact=factor, origin=(c.x, c.y)).intersection(poly).buffer(0)
    if g.geom_type != "Polygon":
        g = max(polygons(g), key=lambda p: p.area)
    return g


def part_dict(geom, floors, floor_height=3.0, base_z=0.0, height_override=None, label="part"):
    height = height_override if height_override is not None else floors * floor_height
    return [
        {"label": label, "coords": coords(p), "area": p.area, "floors": int(floors), "height": float(height), "base_z": float(base_z)}
        for p in clean_polys(geom, min_area=6.0, simplify=0.15)
    ]


def v1(plot):
    spec = VARIANT_SPECS["V1"]
    inner = inward(plot, spec["setback"])
    max_floors = int(spec["max_height"] // spec["floor_height"])
    target_fp = min(inner.area * 0.96, spec["target_far"] * plot.area / max_floors)
    c = inner.centroid
    shell = inner
    lo, hi = 0.05, 0.95
    for _ in range(36):
        f = (lo + hi) / 2
        court = affinity.scale(inner, xfact=f, yfact=f, origin=(c.x, c.y))
        cand = inner.difference(court).buffer(0)
        if cand.area > target_fp:
            lo = f
        else:
            hi = f
        shell = cand
    if shell.is_empty or shell.area < target_fp * 0.55:
        shell = scale_to_area(inner, target_fp)
    parts = part_dict(shell, max_floors, spec["floor_height"], label="courtyard_bars")
    return spec, parts


def v2(plot):
    spec = VARIANT_SPECS["V2"]
    inner = inward(plot, spec["setback"])
    minx, miny, maxx, maxy = inner.bounds
    w, h = maxx - minx, maxy - miny
    left = box(minx, miny, minx + w * 0.48, maxy).intersection(inner)
    bottom = box(minx + w * 0.48, miny, maxx, miny + h * 0.43).intersection(inner)
    fp = unary_union([left, bottom]).buffer(0)
    if fp.is_empty or fp.area < 20:
        fp = inner
        left = inner
        bottom = None
    max_floors = int(spec["max_height"] // spec["floor_height"])
    floors = max(4, min(max_floors, math.ceil(spec["target_far"] * plot.area / max(fp.area, 1))))
    low_floors = max(2, floors - 2)
    parts = []
    parts += part_dict(left, floors, spec["floor_height"], label="tall_L_wing")
    if bottom is not None and not bottom.is_empty:
        parts += part_dict(bottom, low_floors, spec["floor_height"], label="lower_stepped_wing")
    return spec, parts


def v3(plot):
    spec = VARIANT_SPECS["V3"]
    inner = inward(plot, spec["setback"])
    podium_floors = 4
    max_floors = int(spec["max_height"] // spec["floor_height"])
    extra_floors = max_floors - podium_floors
    target_gfa = spec["target_far"] * plot.area
    podium_target = min(inner.area * 0.82, target_gfa * 0.24 / podium_floors)
    podium = scale_to_area(inner, podium_target)
    tower_target = min(inner.area * 0.70, max(60.0, (target_gfa - podium.area * podium_floors) / extra_floors))
    tower = scale_to_area(inner, tower_target)
    parts = []
    parts += part_dict(podium, podium_floors, spec["floor_height"], base_z=0, label="podium")
    parts += part_dict(tower, extra_floors, spec["floor_height"], base_z=podium_floors * spec["floor_height"], label="tower")
    return spec, parts


def v4(plot):
    spec = VARIANT_SPECS["V4"]
    inner = inward(plot, spec["setback"])
    minx, miny, maxx, maxy = inner.bounds
    w, h = maxx - minx, maxy - miny
    # Two separated north-south slabs, scaled toward target FAR.
    slab_w = max(7.0, w * 0.24)
    gap = max(6.0, w * 0.16)
    cx = (minx + maxx) / 2
    left = box(cx - gap / 2 - slab_w, miny, cx - gap / 2, maxy).intersection(inner)
    right = box(cx + gap / 2, miny, cx + gap / 2 + slab_w, maxy).intersection(inner)
    fp = unary_union([left, right]).buffer(0)
    if fp.is_empty or fp.area < 30:
        fp = scale_to_area(inner, inner.area * 0.48)
    max_floors = int(spec["max_height"] // spec["floor_height"])
    floors = max(5, min(max_floors, math.ceil(spec["target_far"] * plot.area / max(fp.area, 1))))
    parts = part_dict(fp, floors, spec["floor_height"], label="parallel_slab")
    return spec, parts


def v5(plot):
    spec = VARIANT_SPECS["V5"]
    inner = inward(plot, spec["setback"])
    max_floors = int(spec["max_height"] // spec["floor_height"])
    target_gfa = spec["target_far"] * plot.area
    base_floors = 4
    base = scale_to_area(inner, min(inner.area * 0.82, target_gfa * 0.50 / base_floors))
    remaining = max(0.0, target_gfa - base.area * base_floors)
    upper_floors = max(1, max_floors - base_floors)
    upper = scale_to_area(inner, min(inner.area * 0.55, remaining / upper_floors if upper_floors else inner.area * 0.4))
    parts = []
    parts += part_dict(base, base_floors, spec["floor_height"], base_z=0, label="terraced_base")
    parts += part_dict(upper, upper_floors, spec["floor_height"], base_z=base_floors * spec["floor_height"], label="setback_upper")
    return spec, parts


def metrics(plot, spec, parts):
    geoms = []
    total_gfa = 0.0
    max_top = 0.0
    max_floors = 0
    for p in parts:
        geom = box(0, 0, 0, 0)
        # Reconstruct only for footprint union from coords.
        from shapely.geometry import Polygon
        poly = Polygon(p["coords"])
        geoms.append(poly)
        floors = int(p["floors"])
        total_gfa += p["area"] * floors
        max_top = max(max_top, p["base_z"] + p["height"])
        max_floors = max(max_floors, int(round((p["base_z"] + p["height"]) / spec["floor_height"])))
    footprint = unary_union(geoms).area if geoms else 0.0
    return {
        "type": spec["type"],
        "plot_area_m2": plot.area,
        "footprint_area_m2": footprint,
        "floors": max_floors,
        "max_height_m": min(max_top, spec["max_height"]),
        "target_far": spec["target_far"],
        "gfa_m2": total_gfa,
        "realised_far": total_gfa / plot.area if plot.area else 0.0,
    }


def main():
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
    minx, miny = tr.transform(W, S)
    maxx, maxy = tr.transform(E, N)
    site = box(minx, miny, maxx, maxy)

    plot = wkt.loads((OUT / "empty_plot.wkt").read_text(encoding="utf-8")).buffer(0)
    if plot.geom_type != "Polygon":
        plot = max(polygons(plot), key=lambda p: p.area)

    buildings = gpd.read_file(DATA / "buildings_3006.gpkg").to_crs("EPSG:3006")
    buildings = gpd.clip(buildings, gpd.GeoDataFrame(geometry=[site], crs="EPSG:3006"))
    scene_buildings = []
    for _, row in buildings.iterrows():
        h = float(row.get("HEIGHT", 12.0) or 12.0)
        h = max(3.0, min(h, 80.0))
        for p in clean_polys(row.geometry, min_area=12.0, simplify=0.35):
            scene_buildings.append({"coords": coords(p), "height": h, "area": p.area})
    # Keep file/render size reasonable but representative.
    scene_buildings = sorted(scene_buildings, key=lambda d: d["area"], reverse=True)[:900]

    variants = {}
    for key, maker in [("V1", v1), ("V2", v2), ("V3", v3), ("V4", v4), ("V5", v5)]:
        spec, parts = maker(plot)
        variants[key] = {"spec": spec, "parts": parts, "metrics": metrics(plot, spec, parts)}

    origin = [round(site.centroid.x, 3), round(site.centroid.y, 3)]
    c = plot.centroid
    fallback_used = "unknown"
    fpath = DATA / "fallback_used.txt"
    if fpath.exists():
        fallback_used = fpath.read_text(encoding="utf-8").strip()
    payload = {
        "crs": "EPSG:3006",
        "site_bounds": [minx, miny, maxx, maxy],
        "origin": origin,
        "plot": {"coords": coords(plot), "area": plot.area, "centroid": [c.x, c.y]},
        "buildings": scene_buildings,
        "variants": variants,
        "fallback_used": fallback_used,
    }
    (OUT / "scene_data.json").write_text(json.dumps(payload), encoding="utf-8")
    log(f"Prepared Blender scene data: {len(scene_buildings)} context building parts; plot area {plot.area:.1f} m²")


if __name__ == "__main__":
    main()
