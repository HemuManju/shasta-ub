"""Locate (and download on first use) the OSM2World jar used to build maps."""

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

RELEASE_URL = (
    "https://github.com/HemuManju/shasta-ub/releases/download/"
    "osm2world-v1/osm2world.zip"
)
CACHE_DIR = Path(os.environ.get("SHASTA_CACHE", Path.home() / ".cache" / "shasta"))
JAR_NAME = "OSM2WORLD.jar"


def _candidates():
    env = os.environ.get("SHASTA_OSM2WORLD")
    if env:
        yield Path(env)
    yield Path(__file__).resolve().parents[2] / "tools" / "osm2world"
    yield CACHE_DIR / "osm2world"


def find_osm2world():
    """Return the directory holding ``OSM2WORLD.jar`` and ``lib/``, or None."""
    for folder in _candidates():
        if (folder / JAR_NAME).exists() and (folder / "lib").is_dir():
            return folder
    return None


def download_osm2world(url=RELEASE_URL):
    """Download and unpack the jar (about 27 MB) into the user cache."""
    target = CACHE_DIR / "osm2world"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    archive = CACHE_DIR / "osm2world.zip"
    print(f"Downloading OSM2World from {url} ...")
    try:
        _download(url, archive)
    except OSError as exc:
        raise RuntimeError(
            f"Could not download OSM2World ({exc}). Download osm2world.zip "
            f"manually, unzip it, and set SHASTA_OSM2WORLD to the folder that "
            f"contains {JAR_NAME} and lib/."
        ) from exc
    shutil.rmtree(target, ignore_errors=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(target)
    archive.unlink()
    return target


def ensure_osm2world():
    return find_osm2world() or download_osm2world()


JAVA_MINIMUM = 11
JAVA_CACHE = CACHE_DIR / "jdk"


def _download(url, target):
    """Fetch ``url`` to ``target`` (some hosts reject urllib's default user agent)."""
    request = urllib.request.Request(url, headers={"User-Agent": "shasta-setup"})
    with urllib.request.urlopen(request, timeout=120) as response, open(target, "wb") as out:
        shutil.copyfileobj(response, out)


def _java_major(java):
    """Major version of a java executable, or None if it cannot be read."""
    try:
        out = subprocess.run(
            [str(java), "-version"], capture_output=True, text=True, timeout=30
        ).stderr
        first = out.split('"')[1].split(".")[0].split("-")[0].split("+")[0]
        return int(first)
    except (OSError, IndexError, ValueError, subprocess.SubprocessError):
        return None


def _java_candidates():
    exe = "java.exe" if os.name == "nt" else "java"
    if JAVA_CACHE.exists():
        yield from sorted(JAVA_CACHE.rglob(f"bin/{exe}"))
    home = os.environ.get("JAVA_HOME")
    if home:
        yield Path(home) / "bin" / exe
    on_path = shutil.which("java")
    if on_path:
        yield Path(on_path)


def find_java(minimum=JAVA_MINIMUM):
    """Path to a Java runtime of at least ``minimum``, or None."""
    for candidate in _java_candidates():
        version = _java_major(candidate)
        if version is not None and version >= minimum:
            return candidate
    return None


def download_java(version=JAVA_MINIMUM):
    """Download a small Java runtime (Temurin JRE, about 45 MB) into the user cache."""
    system = {"linux": "linux", "darwin": "mac", "win32": "windows"}.get(sys.platform)
    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x64" if machine in ("x86_64", "amd64") else None
    if system is None or arch is None:
        raise RuntimeError(f"No automatic Java download for {sys.platform}/{machine}; install Java {version}+ manually.")
    url = f"https://api.adoptium.net/v3/binary/latest/{version}/ga/{system}/{arch}/jre/hotspot/normal/eclipse"
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    archive = CACHE_DIR / ("jre.zip" if system == "windows" else "jre.tar.gz")
    print(f"Downloading Java {version} from Adoptium (about 45 MB) ...")
    try:
        _download(url, archive)
    except OSError as exc:
        raise RuntimeError(
            f"Could not download Java ({exc}). Install Java {version}+ from https://adoptium.net instead."
        ) from exc
    shutil.rmtree(JAVA_CACHE, ignore_errors=True)
    JAVA_CACHE.mkdir(parents=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(JAVA_CACHE)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(JAVA_CACHE)
    archive.unlink()
    java = find_java(version)
    if java is None:
        raise RuntimeError("Java was downloaded but could not be run; install Java manually.")
    if os.name != "nt":
        java.chmod(0o755)
    return java


def check_java(minimum=JAVA_MINIMUM):
    """Return the path of a suitable ``java`` or raise an error that says how to get one."""
    java = find_java(minimum)
    if java is None:
        raise RuntimeError(
            f"Java {minimum}+ is required to build maps but was not found. "
            "Run `shasta setup-java` to download it (no admin rights needed), or install it "
            "from https://adoptium.net."
        )
    return str(java)
