import numpy as np

from shasta.actors import UAV, UGV
from shasta.config import load_config
from shasta.env import ShastaEnv
from shasta.experiments import GoToNodeExperiment


def run_demo(gui=False, map_name='buffalo-small', n_uav=4, n_ugv=3, steps=2000):
    """Send a UAV group and a UGV group to random map nodes and report progress."""
    config = load_config(headless=not gui)
    config['experiment'] = {'map_to_use': map_name, 'type': GoToNodeExperiment}

    groups = {0: [UAV() for _ in range(n_uav)], 1: [UGV() for _ in range(n_ugv)]}
    env = ShastaEnv(config, groups)
    obs, _ = env.reset()

    n_nodes = len(env.core.get_map().get_node_graph().nodes)
    rng = np.random.default_rng(0)
    targets = {g: int(rng.integers(n_nodes)) for g in groups}
    print(f"Targets (map nodes): {targets}")

    obs, _, done, _, _ = env.step(targets)
    for step in range(steps):
        obs, _, done, _, _ = env.step(None)
        if step % 50 == 0 or done:
            centroids = {g: obs[g].mean(axis=0)[:2].round(1).tolist() for g in obs}
            print(f"step {step:4d} centroids {centroids}")
        if done:
            print(f"All groups reached their targets after {step} steps.")
            break
    else:
        print(f"Stopped after {steps} steps.")
    env.close()
    return obs
