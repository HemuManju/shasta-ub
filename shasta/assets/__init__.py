"""Locate SHASTA assets (vehicle models and maps).

Search order for a named map or file:

1. ``$SHASTA_ASSETS`` (a directory you control, e.g. a full copy of the maps)
2. ``./assets`` in the current working directory
3. the assets bundled inside the installed package
"""

import os
from pathlib import Path

_BUNDLED = Path(__file__).resolve().parent


def _search_roots():
    roots = []
    env = os.environ.get("SHASTA_ASSETS")
    if env:
        roots.append(Path(env))
    roots.append(Path.cwd() / "assets")
    roots.append(_BUNDLED)
    return roots


def get_asset_path(*parts):
    """Return the first existing path for ``parts`` (e.g. ``"vehicles", "x.urdf"``)."""
    for root in _search_roots():
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(
        f"Asset '{'/'.join(parts)}' not found. Searched: "
        + ", ".join(str(r) for r in _search_roots())
        + ". Set SHASTA_ASSETS to a folder containing it."
    )


def list_maps():
    """Names of the maps that can currently be found."""
    names = set()
    for root in _search_roots():
        if root.is_dir():
            names.update(
                p.name for p in root.iterdir() if (p / "coordinates.csv").exists()
            )
    return sorted(names)


assets_root = str(_BUNDLED)
