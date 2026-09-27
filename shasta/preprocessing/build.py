"""Turn an OpenStreetMap extract into a SHASTA map.

Pipeline: ``.osm`` -> OSM2World (3D mesh + ``coordinates.csv``, the point pairs
that tie map latitude/longitude to simulator coordinates) -> asset folder
that :class:`shasta.map.Map` and pybullet can load.
"""

import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .osm2world import JAR_NAME, check_java, ensure_osm2world

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

URDF_TEMPLATE = """<?xml version="1.0" ?>
<robot name="environment">
<link name="buildings">
  <inertial>
    <origin rpy="0 0 0" xyz="0 0 0"/>
    <mass value="0"/>
    <inertia ixx="0" ixy="0" ixz="0" iyy="0" iyz="0" izz="0"/>
  </inertial>
  <visual>
    <origin rpy="0 0 0" xyz="0 0 0"/>
    <geometry>
      <mesh filename="meshes/map.obj"/>
    </geometry>
  </visual>
</link>
</robot>
"""


def fetch_osm(south, west, north, east, out_path):
    """Download roads and buildings inside a bounding box from Overpass.

    Keep the box small (a campus or a few blocks, up to about 2 km across):
    the 3D mesh and the simulation grow quickly with area.
    """
    if not (south < north and west < east):
        raise ValueError("Bounding box must satisfy south < north and west < east")
    query = (
        f"[out:xml][timeout:120][bbox:{south},{west},{north},{east}];"
        "(way[highway];way[building];relation[building];);"
        "(._;>;);out;"
    )
    data = urllib.parse.urlencode({"data": query}).encode()
    errors = []
    for url in OVERPASS_URLS:
        request = urllib.request.Request(
            url, data=data, headers={"User-Agent": "shasta-build-map"}
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                content = response.read()
        except OSError as exc:
            errors.append(f"{url}: {exc}")
            continue
        Path(out_path).write_bytes(content)
        return Path(out_path)
    raise RuntimeError(
        "All Overpass servers failed:\n  " + "\n  ".join(errors)
        + "\nTry again in a minute, or export the area as .osm from "
        "https://www.openstreetmap.org (Export tab) and pass that file to `shasta build-map`."
    )


def calibration_error(coordinates_csv):
    """RMSE (metres) of the lat/lon -> simulator affine fit in ``coordinates.csv``."""
    points = pd.read_csv(coordinates_csv)
    source = np.hstack([points[["lat", "lon"]].values, np.ones((len(points), 1))])
    target = points[["x", "z"]].values
    A, *_ = np.linalg.lstsq(source, target, rcond=None)
    residual = source @ A - target
    return float(np.sqrt((residual**2).sum(axis=1).mean()))


def build_map(osm_path, name, out_dir="assets", overwrite=False, config=None):
    """Build the asset folder ``out_dir/name`` from ``osm_path``.

    Returns the folder. Requires Java 11+; the OSM2World jar is downloaded on
    first use (see :mod:`shasta.preprocessing.osm2world`).
    """
    osm_path = Path(osm_path)
    if not osm_path.exists():
        raise FileNotFoundError(osm_path)
    target = Path(out_dir) / name
    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists (use overwrite=True)")

    java = check_java()
    tool_dir = ensure_osm2world()
    config = Path(config) if config else tool_dir / "texture_config.properties"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        shutil.copy(osm_path, tmp / "map.osm")
        command = [java, "-jar", str(tool_dir / JAR_NAME)]
        if config.exists():
            command += ["--config", str(config)]
        command += ["-i", str(tmp / "map.osm"), "-o", str(tmp / "map.obj")]
        result = subprocess.run(command, cwd=tmp, capture_output=True, text=True)
        for produced in ("map.obj", "coordinates.csv"):
            if not (tmp / produced).exists():
                raise RuntimeError(
                    f"OSM2World did not produce {produced}:\n{result.stdout[-1500:]}"
                    f"\n{result.stderr[-1500:]}"
                )

        shutil.rmtree(target, ignore_errors=True)
        (target / "meshes").mkdir(parents=True)
        shutil.copy(tmp / "map.osm", target / "map.osm")
        shutil.copy(tmp / "coordinates.csv", target / "coordinates.csv")
        for mesh_file in tmp.glob("map.obj*"):
            shutil.copy(mesh_file, target / "meshes" / mesh_file.name)

    (target / "environment_collision_free.urdf").write_text(URDF_TEMPLATE)
    return target
