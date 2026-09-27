"""Zip OSM2WORLD.jar + lib/ into osm2world.zip (attach it to a GitHub release).

Run from the repo root: python tools/make_osm2world_release.py
"""

import zipfile
from pathlib import Path

folder = Path(__file__).resolve().parent / "osm2world"
out = Path("osm2world.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in [folder / "OSM2WORLD.jar", folder / "texture_config.properties"]:
        zf.write(path, path.name)
    for path in (folder / "lib").iterdir():
        zf.write(path, f"lib/{path.name}")
print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
