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
shasta demo            # headless: prints swarm progress
shasta demo --gui      # opens the 3D pybullet window
shasta maps            # list the maps available
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

Map nodes are the intersections of the OpenStreetMap street graph;
`env.core.get_map().get_node_graph()` gives you the graph and
`get_cartesian_node_position(i)` gives the simulator coordinates of node `i`.

## Build your own experiment

Subclass `shasta.base_experiment.BaseExperiment` and implement `apply_actions`, `get_observation`,
`get_done_status` and `compute_reward`. [shasta/experiments.py](shasta/experiments.py) is a
complete, short example. Custom vehicles subclass `shasta.actors.BaseActor`
(see [shasta/actors/vehicles.py](shasta/actors/vehicles.py)). Reusable swarm behaviours live in
`shasta.primitives` (`Formation`, `PathPlanning`).

## Maps

The wheel ships with `buffalo-small` (about 2 MB). The larger maps (Buffalo medium/large, Chicago, New York, San Jose, ...)
are in the [`assets/`](assets/) folder of this repository. To use them, clone the repo and either run from the
repository root or point `SHASTA_ASSETS` to that folder:

```bash
export SHASTA_ASSETS=/path/to/shasta/assets
```

then set `config['experiment']['map_to_use'] = 'buffalo-medium'`.

## Development

```bash
git clone <this repository>
cd shasta
pip install -e ".[test]"
pytest
```

## Notes

- The pyglet GUI in `gui/` and the reinforcement-learning `experiments/complex_experiment/` are research code
  that is not part of the installable package.
- Creating new maps from `.osm` files needs Java (OSM2World) and Blender; see `shasta/preprocessing/`.

## License

MIT, see [LICENSE](LICENSE).
