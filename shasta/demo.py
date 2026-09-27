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


def run_gui(map_name='buffalo-small', n_uav_groups=2, n_ugv_groups=2, uavs=4, ugvs=3,
            n_targets=3, time_limit=None, seed=None):
    """Open the human interface: command UAV/UGV groups to reach mission targets."""
    import random

    from shasta.gui import ShastaGUI
    from shasta.interaction import Mission, SwarmCommander

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    config = load_config(headless=True)
    config['experiment'] = {'map_to_use': map_name, 'type': GoToNodeExperiment}

    groups = {}
    for _ in range(n_uav_groups):
        groups[len(groups)] = [UAV() for _ in range(uavs)]
    for _ in range(n_ugv_groups):
        groups[len(groups)] = [UGV() for _ in range(ugvs)]

    env = ShastaEnv(config, groups)
    mission = Mission.random(env.core.get_map(), n_targets, seed=seed, time_limit=time_limit)
    gui = ShastaGUI(SwarmCommander(env, mission))
    gui.run()
    env.close()
