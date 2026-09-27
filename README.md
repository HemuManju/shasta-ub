# SHASTA

**S**imulator for **H**uman-Autonomy and **S**warm **T**eaming **A**pplications.
A [pybullet](https://pybullet.org) simulator for studying human-swarm interaction on real city maps
(built from OpenStreetMap). Swarms of aerial (UAV) and ground (UGV) vehicles move in formation along
the street network, and a Gymnasium interface lets a human, a scripted policy or an RL agent command them.

## Install

```bash
pip install ihuman-shasta
```

The PyPI name is `ihuman-shasta`; the Python package is `shasta`. Python 3.9 or newer.

## Try it in 30 seconds

```bash
pip install "ihuman-shasta[gui]"   # [gui] adds the human interface
shasta gui                         # command UAV/UGV groups on the map yourself
shasta demo                        # headless: prints swarm progress
shasta maps                        # list the maps available
```

## Human interface

`shasta gui` opens a top-down map with your swarm groups (blue UAVs, red UGVs) and mission targets.

| Action | How |
| --- | --- |
| Pick a group | click its marker, click its button, or press `1`-`9` |
| Pick a target | click near a street node (a white cross marks it) |
| Send the group | `Enter`, the **Send order** button, or double-click the node |
| Send everyone | **Send ALL groups** |
| Cancel an order | **Cancel order** |
| Pause / speed | `Space`, `-` / `+` |
| Zoom / pan | mouse wheel / right-drag, `R` resets the view |
| 3D camera view | `V` (follows the selected group) |

The side panel shows mission progress, the selected group's battery, ammo, distance and ETA, and an event log.
Options: `--map`, `--uav-groups`, `--ugv-groups`, `--targets`, `--time-limit`, `--seed`.

The GUI is a thin layer over `shasta.interaction.SwarmCommander`, which you can drive from Python
(scripted humans, AI advisors, experiments) with no window:

```python
from shasta.interaction import Mission, SwarmCommander

commander = SwarmCommander(env, Mission.random(env.core.get_map(), 3, seed=0))
commander.send(0, commander.mission.targets[0])   # group 0 -> first target
while not commander.mission.is_complete():
    commander.update()
print(commander.events)
```

## Use it from Python

```python
from shasta.actors import UAV, UGV
from shasta.config import load_config
from shasta.env import ShastaEnv
from shasta.experiments import GoToNodeExperiment

config = load_config(headless=True)          # headless=False opens the 3D window
config['experiment']['type'] = GoToNodeExperiment

groups = {0: [UAV() for _ in range(4)],      # group 0: four drones
          1: [UGV() for _ in range(3)]}      # group 1: three ground vehicles

env = ShastaEnv(config, groups)
obs, info = env.reset()                      # obs = {group_id: (n_actors, 3) positions}

# Order both groups to map-graph node 5; they plan a route and fly/drive in formation
obs, reward, terminated, truncated, info = env.step({0: 5, 1: 5})
while not terminated:
    obs, reward, terminated, truncated, info = env.step(None)  # None = keep going
env.close()
```

Map nodes are the intersections of the OpenStreetMap street graph. Only roads are used for routing
(motorway through service roads); footpaths, plazas, steps and building outlines are ignored, and
`config['experiment']['road_types']` overrides the list.
`env.core.get_map().get_node_graph()` gives you the graph and
`get_cartesian_node_position(i)` gives the simulator coordinates of node `i`.

## Build your own experiment

Subclass `shasta.base_experiment.BaseExperiment` and implement `apply_actions`, `get_observation`,
`get_done_status` and `compute_reward`. [shasta/experiments.py](shasta/experiments.py) is a
complete, short example. Custom vehicles subclass `shasta.actors.BaseActor`
(see [shasta/actors/vehicles.py](shasta/actors/vehicles.py)). Reusable swarm behaviours live in
`shasta.primitives` (`Formation`, `PathPlanning`).

## Maps

The wheel ships with `buffalo-small` (about 2 MB). Larger maps (Buffalo medium/large, Chicago, New York, San Jose, ...)
are in the [`assets/`](assets/) folder of this repository; use them by running from the repository root or by setting
`SHASTA_ASSETS=/path/to/shasta/assets`, then `shasta gui --map buffalo-medium`.

### Build a map of any place

```bash
shasta fetch-osm --bbox 43.000 -78.792 43.006 -78.783 -o campus.osm   # south west north east
shasta build-map campus.osm --name campus                             # creates ./assets/campus
shasta gui --map campus
```

`build-map` runs the custom OSM2World tool, which writes the 3D mesh and `coordinates.csv`: matched
(latitude, longitude) and simulator (x, y) points. SHASTA fits an affine transform to them, which is how street
routes, buildings and vehicles line up with the 3D world (`build-map` prints the fit error, normally 0.00 m).
Keep the area to a campus or a few blocks (up to about 2 km across). If the Overpass servers are busy,
export the area as `.osm` from [openstreetmap.org](https://www.openstreetmap.org) (Export tab) instead.

Requirements: Java 11 or newer, only for `build-map`. No Java? Run `shasta setup-java` (about 45 MB download,
no admin rights, stored in `~/.cache/shasta`), or install it from [adoptium.net](https://adoptium.net) /
`conda install -c conda-forge openjdk`. `shasta build-map` also offers to download it when it is missing.
The OSM2World jar (about 26 MB) downloads on first use into the same cache; set `SHASTA_OSM2WORLD` to use a local copy.

**Maintainers:** run `python tools/make_osm2world_release.py`, then
`gh release create osm2world-v1 osm2world.zip --title "OSM2World tool"` (or attach `osm2world.zip` to a release tagged
`osm2world-v1` on GitHub). The download URL is `RELEASE_URL` in `shasta/preprocessing/osm2world.py`; keep it in sync
with the repository that hosts the release.

## Development

```bash
git clone <this repository>
cd shasta
pip install -e ".[test,gui]"
pytest
```

## Notes

- The reinforcement-learning `experiments/complex_experiment/` is research code that is not part of the
  installable package. The old pyglet viewer in `gui/` is superseded by `shasta gui`.
- Blender is no longer needed: the OSM2World mesh loads in pybullet directly.

## License

MIT, see [LICENSE](LICENSE).
