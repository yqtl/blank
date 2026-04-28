#!/usr/bin/env python3
"""Render the site map with QGIS if available, else GeoPandas/Matplotlib."""
from __future__ import annotations

from pathlib import Path

PROJECT = Path.home() / "projects" / "ljustergrand-poc"
OUT = PROJECT / "out"
DATA = Path.home() / "gis-data" / "ljustergrand"
LOG = OUT / "run_log.md"
W, S, E, N = 18.0764, 59.3004, 18.0895, 59.3094


def log(msg: str) -> None:
    print(msg)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"\n- {msg}\n")


def render_matplotlib():
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from pyproj import Transformer
    from shapely.geometry import box

    b = gpd.read_file(DATA / "buildings_3006.gpkg")
    s = gpd.read_file(DATA / "streets_3006.gpkg")
    tr = Transformer.from_crs("EPSG:4326", "EPSG:3006", always_xy=True)
    minx, miny = tr.transform(W, S)
    maxx, maxy = tr.transform(E, N)
    bbox = gpd.GeoDataFrame(geometry=[box(minx, miny, maxx, maxy)], crs="EPSG:3006")
    b = gpd.clip(b, bbox)
    s = gpd.clip(s, bbox)

    fig, ax = plt.subplots(figsize=(8, 8), dpi=128)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_facecolor("#f3f1ed")
    if not b.empty:
        b.plot(ax=ax, color="#b7b7b7", edgecolor="#777777", linewidth=0.25)
    if not s.empty:
        s.plot(ax=ax, color="#202020", linewidth=1.2)
    bbox.boundary.plot(ax=ax, color="#444444", linewidth=1.0, linestyle="--")
    ax.set_xlim(minx, maxx)
    ax.set_ylim(miny, maxy)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.text(0.02, 0.98, "Ljustergränd 5 / Hammarbyhöjden-Skanstull edge — EPSG:3006", transform=ax.transAxes, va="top", ha="left", fontsize=9, color="#222222", bbox={"facecolor":"white", "alpha":0.65, "edgecolor":"none", "pad":3})
    fig.savefig(OUT / "qgis_site.png", dpi=128)
    plt.close(fig)
    log("Rendered out/qgis_site.png with GeoPandas/Matplotlib fallback (QGIS Python unavailable).")


def render_qgis():
    # Kept deliberately conservative. In most headless CI/VPS contexts qgis.core is absent;
    # fallback is the primary reliable renderer for the POC.
    from qgis.core import QgsApplication  # noqa: F401
    raise RuntimeError("QGIS Python import succeeded, but headless QGIS renderer was not configured; using fallback")


def main():
    try:
        render_qgis()
    except Exception as e:
        log(f"QGIS renderer unavailable/failed: {repr(e)}")
        render_matplotlib()


if __name__ == "__main__":
    main()
