# Build a map of any place

Step 4 of `01_shasta_hsi.ipynb` turns a bounding box into a SHaSTA map from OpenStreetMap data. This page is the setup for it, and the same thing from a terminal.
The full guide is [`docs/building_maps.rst`](../docs/building_maps.rst).

## What it needs

| Need | Why | Only for |
|---|---|---|
| Java 11 or newer | OSM2World, the tool that makes the 3D mesh, is a Java program | building a map |
| The internet | the roads and buildings come from the Overpass service, and the OSM2World tool (about 26 MB) is downloaded once from this repository's GitHub release | building a map |

Playing on a map that is already built needs neither.

## 1. Install Java

Check first: `java -version` should print 11 or higher.

On the tutorial server, as an administrator, install it for the whole machine so every user's notebook finds it on its `PATH` (a Java installed inside the `smc` conda environment is not on the
`PATH` of the notebook kernel):

```bash
sudo apt-get install -y default-jre-headless
java -version
```

The same applies to SHaSTA itself: install it into the `smc` environment as an administrator (`sudo /opt/tljh/user/envs/smc/bin/python -m pip install ...`), not with a plain `pip install` from a user
account, which puts it in that one user's `~/.local`.

Anywhere else, without administrator rights (about 45 MB, stored in `~/.cache/shasta`):

```bash
shasta setup-java
```

The notebook cell also does this by itself when there is no Java.

## 2. Build the map

In the notebook, change `PLACE` and `BBOX` (south, west, north, east) in Step 4 and run the cell. From a terminal, the same three steps:

```bash
shasta fetch-osm --bbox 47.612 -122.206 47.618 -122.198 -o bellevue.osm    # south west north east
shasta build-map bellevue.osm --name bellevue                               # makes ./assets/bellevue
shasta demo --map bellevue                                                  # try it, no window
```

`build-map` prints the calibration error, normally under 0.01 m. Use the map in `config.yaml` with `experiment: map_to_use: bellevue`. SHaSTA looks for the folder
in `$SHASTA_ASSETS`, then `./assets` next to where you run it, then the maps shipped with the package.

Get a box by right-clicking two corners on [openstreetmap.org](https://www.openstreetmap.org) and reading the latitude and longitude, or use its *Export* tab and pass the
downloaded `.osm` file to `build-map`. Keep it to a campus or a few blocks, up to about 2 km across: the 3D world grows quickly with the area.

## On the shared server

- **Each user builds into their own folder**, `assets/` next to their copy of the notebook, so nobody overwrites anyone.
- **Everyone fetches from the same address.** If many people fetch at once, the Overpass service may refuse some of them (the error says all servers failed). Wait a minute and run
  the cell again, or build the map once yourself and give people the `bellevue.osm` file to put next to the notebook.
- **One copy of the tool for everyone.** Unzip `osm2world.zip` once into a shared folder and set `SHASTA_OSM2WORLD` to it, so each user does not download 26 MB:
  `export SHASTA_OSM2WORLD=/path/to/shared/osm2world` (the folder that holds `OSM2WORLD.jar` and `lib/`).

## When something fails

| Message | Fix |
|---|---|
| `Java 11+ is required to build maps but was not found` | Step 1. Java 8 does not work. |
| `All Overpass servers failed` | The service is busy: wait and run again, or export the area from openstreetmap.org and use `build-map`. |
| `Could not download OSM2World` | No route to GitHub. Download `osm2world.zip` by hand, unzip it, and set `SHASTA_OSM2WORLD`. |
| `... already exists` | The map name is taken. Choose another `PLACE`, or pass `overwrite=True` (the notebook already does). |
