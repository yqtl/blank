#!/usr/bin/env python3
"""Blender 4.5 script: context buildings, empty plot, three massing variants, GLBs/renders/report."""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PROJECT = Path.home() / "projects" / "stockholm-poc"
OUT = PROJECT / "out"
LOG = OUT / "run_log.md"


def log(msg: str) -> None:
    print(msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n- {msg}\n")


def run_prepare():
    py = PROJECT / ".venv" / "bin" / "python"
    if not py.exists():
        py = Path(sys.executable)
    cmd = [str(py), str(PROJECT / "_prepare_scene_data.py")]
    log("Preparing scene data with command: " + " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(PROJECT))


def make_mat(name, color):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def local_xy(pt, origin):
    return (pt[0] - origin[0], pt[1] - origin[1])


def add_extruded_polygon(name, xy, height, base_z, mat, collection, origin):
    if len(xy) < 4:
        return None
    pts = xy[:-1] if xy[0] == xy[-1] else xy
    if len(pts) < 3:
        return None
    verts = []
    for p in pts:
        x, y = local_xy(p, origin)
        verts.append((x, y, base_z))
    for p in pts:
        x, y = local_xy(p, origin)
        verts.append((x, y, base_z + height))
    n = len(pts)
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    for i in range(n):
        faces.append((i, (i + 1) % n, (i + 1) % n + n, i + n))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    collection.objects.link(obj)
    return obj


def add_flat_polygon(name, xy, z, mat, collection, origin):
    pts = xy[:-1] if xy[0] == xy[-1] else xy
    verts = []
    for p in pts:
        x, y = local_xy(p, origin)
        verts.append((x, y, z))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], [tuple(range(len(verts)))])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.data.materials.append(mat)
    collection.objects.link(obj)
    return obj


def look_at(obj, target):
    loc = obj.location
    direction = Vector(target) - loc
    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def set_collection_visibility(coll, visible):
    for obj in coll.objects:
        obj.hide_viewport = not visible
        obj.hide_render = not visible
    for child in coll.children:
        set_collection_visibility(child, visible)


def write_report(data, renderer_name):
    plot = data["plot"]
    centroid = plot["centroid"]
    lines = []
    lines.append("# Stockholm Urban Massing POC — Skanstull / Hammarby Sluss")
    lines.append("")
    lines.append("## Site description")
    lines.append("Conceptual one-day massing demo for Skanstull / Hammarby Sluss, southern Södermalm, Stockholm. Work is in EPSG:3006 / SWEREF 99 TM using the requested WGS84 bbox 18.0695,59.3050,18.0782,59.3105.")
    lines.append("")
    lines.append("## Data sources used")
    lines.append("- OpenStreetMap building footprints and street network via OSMnx/Overpass, projected to EPSG:3006.")
    if str(data.get("fallback_used", "unknown")).lower() == "yes":
        lines.append("- Synthetic EPSG:3006 fallback context was used because live OSM/Overpass retrieval failed.")
    lines.append("- Empty plot derived by subtracting building footprints and buffered street geometry from the site bbox.")
    lines.append("")
    lines.append("## Empty plot")
    lines.append(f"- Area: {plot['area']:.1f} m²")
    lines.append(f"- Centroid EPSG:3006: ({centroid[0]:.2f}, {centroid[1]:.2f})")
    lines.append("")
    lines.append("## Variant metrics")
    lines.append("")
    lines.append("| Variant | Type | Plot area m² | Footprint area m² | Floors | Max height m | Target FAR | GFA m² | Realised FAR |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for key in ["V1", "V2", "V3"]:
        m = data["variants"][key]["metrics"]
        lines.append(f"| {key} | {m['type']} | {m['plot_area_m2']:.1f} | {m['footprint_area_m2']:.1f} | {m['floors']} | {m['max_height_m']:.1f} | {m['target_far']:.1f} | {m['gfa_m2']:.1f} | {m['realised_far']:.2f} |")
    lines.append("")
    lines.append("## Limitations")
    lines.append("- OSM building heights are approximate: `building:levels × 3 m`, otherwise 12 m fallback.")
    lines.append("- DEM/terrain was omitted unless already available; this POC uses flat EPSG:3006 geometry.")
    lines.append("- Massing is conceptual and not a planning-compliant architectural proposal.")
    lines.append("- FAR is approximate due to simplified geometry and conceptual stepped/tower volumes.")
    lines.append(f"- Rendered with Blender {bpy.app.version_string} using {renderer_name}; QGIS preview may use Matplotlib fallback if QGIS Python is unavailable.")
    lines.append("")
    lines.append("## Reproduce")
    lines.append("```bash")
    lines.append("cd ~/projects/stockholm-poc")
    lines.append("python3 -m venv .venv")
    lines.append("source .venv/bin/activate")
    lines.append("pip install --upgrade pip")
    lines.append("pip install 'osmnx>=2.1' geopandas rasterio pyproj momepy shapely fiona matplotlib")
    lines.append("python fetch_data.py")
    lines.append("python create_qgis_preview.py")
    lines.append("python find_empty_plot.py")
    lines.append("./blender/blender --background --python create_blender_demo.py")
    lines.append("```")
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log("Wrote out/report.md")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    run_prepare()
    data = json.loads((OUT / "scene_data.json").read_text(encoding="utf-8"))
    origin = data["origin"]

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    context_coll = bpy.data.collections.new("Context")
    plot_coll = bpy.data.collections.new("EmptyPlot")
    variants_coll = bpy.data.collections.new("Variants")
    bpy.context.scene.collection.children.link(context_coll)
    bpy.context.scene.collection.children.link(plot_coll)
    bpy.context.scene.collection.children.link(variants_coll)

    mats = {
        "context": make_mat("neutral grey context", (0.58, 0.58, 0.56, 1.0)),
        "plot": make_mat("selected empty plot amber", (1.0, 0.82, 0.12, 0.78)),
        "V1": make_mat("V1 warm grey", (0.68, 0.62, 0.54, 1.0)),
        "V2": make_mat("V2 terracotta", (0.76, 0.32, 0.18, 1.0)),
        "V3": make_mat("V3 blue grey glass", (0.34, 0.50, 0.62, 1.0)),
    }

    for i, b in enumerate(data["buildings"]):
        add_extruded_polygon(f"context_{i:04d}", b["coords"], b["height"], 0.0, mats["context"], context_coll, origin)
    add_flat_polygon("selected_empty_plot", data["plot"]["coords"], 0.08, mats["plot"], plot_coll, origin)

    variant_collections = {}
    for key in ["V1", "V2", "V3"]:
        vc = bpy.data.collections.new(data["variants"][key]["spec"]["name"])
        variants_coll.children.link(vc)
        variant_collections[key] = vc
        for j, part in enumerate(data["variants"][key]["parts"]):
            # Clamp at 60 m absolute top height.
            top = min(60.0, part["base_z"] + part["height"])
            height = max(0.5, top - part["base_z"])
            add_extruded_polygon(f"{key}_{j:02d}_{part['label']}", part["coords"], height, part["base_z"], mats[key], vc, origin)

    # Camera, lighting, renderer.
    minx, miny, maxx, maxy = data["site_bounds"]
    span = max(maxx - minx, maxy - miny)
    bpy.ops.object.light_add(type='SUN', location=(0, 0, span))
    sun = bpy.context.object
    sun.name = "Sun"
    sun.data.energy = 2.2
    sun.rotation_euler = (math.radians(42), 0, math.radians(135))
    bpy.ops.object.light_add(type='AREA', location=(0, -span * 0.45, span * 0.7))
    area = bpy.context.object
    area.name = "Soft ambient area"
    area.data.energy = 350
    area.data.size = span
    bpy.context.scene.world.color = (0.78, 0.82, 0.88)

    bpy.ops.object.camera_add(location=(0, -span * 0.95, span * 0.68))
    cam = bpy.context.object
    look_at(cam, (0, 0, 8))
    cam.data.lens = 32
    cam.data.clip_end = 10000
    bpy.context.scene.camera = cam

    renderer = "BLENDER_WORKBENCH"
    try:
        bpy.context.scene.render.engine = renderer
        bpy.context.scene.display.shading.light = 'STUDIO'
        bpy.context.scene.display.shading.color_type = 'MATERIAL'
        bpy.context.scene.display.shading.show_shadows = True
    except Exception:
        pass
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.film_transparent = False

    for key in ["V1", "V2", "V3"]:
        for k, vc in variant_collections.items():
            set_collection_visibility(vc, k == key)
        set_collection_visibility(context_coll, True)
        set_collection_visibility(plot_coll, True)
        bpy.context.scene.render.filepath = str(OUT / f"{key}.png")
        bpy.ops.render.render(write_still=True)
        log(f"Rendered out/{key}.png")
        bpy.ops.export_scene.gltf(filepath=str(OUT / f"{key}.glb"), export_format='GLB', use_visible=True)
        log(f"Exported out/{key}.glb")

    write_report(data, renderer)
    log("Blender demo complete.")


if __name__ == "__main__":
    main()
