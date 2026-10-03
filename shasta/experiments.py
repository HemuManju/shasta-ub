"""Ready-made experiments to start from."""

import numpy as np
from gymnasium import spaces

from shasta.base_experiment import BaseExperiment
from shasta.primitives import Formation, PathPlanning


class GoToNodeExperiment(BaseExperiment):
    """Every actor group flies/drives to a node of the map graph in formation.

    ``env.step(actions)`` takes ``{group_id: node_index}`` (or ``None`` to keep
    the current targets) and advances the simulation one tick. The observation is
    ``{group_id: (n_actors, 3) positions}``; the episode ends when every group
    centroid is within ``tolerance`` metres of its target.
    """

    tolerance = 3.0

    def __init__(self, config, core, experiment_config=None, *args, **kwargs):
        super().__init__(config, core, experiment_config, *args, **kwargs)
        self.planner = PathPlanning(core.get_map())
        self.formation = Formation()
        self.targets = {}
        self.paths = {}

    def get_action_space(self):
        n_nodes = len(self.core.get_map().get_node_graph().nodes)
        return spaces.Discrete(n_nodes)

    def get_observation_space(self):
        return spaces.Box(-np.inf, np.inf, shape=(3,), dtype=np.float64)

    def set_target(self, group_id, node):
        actors = self.core.get_actors_by_group_id(group_id)
        for actor in actors:
            actor.current_pos = actor.get_pos_and_orientation()[0]
        centroid = np.mean([a.current_pos for a in actors], axis=0)
        self.targets[group_id] = node
        path = self.planner.find_path(start=centroid, end=node)
        if len(path) == 0:                      # already at that intersection: the route has no segments, so go to the node itself
            path = np.array([self.planner.map.get_cartesian_node_position(node)])
        self.paths[group_id] = path

    def apply_actions(self, actions, core):
        for group_id, node in (actions or {}).items():
            self.set_target(group_id, node)

        for group_id, path in self.paths.items():
            actors = core.get_actors_by_group_id(group_id)
            for actor in actors:
                actor.current_pos = actor.get_pos_and_orientation()[0]
            centroid = np.mean([a.current_pos for a in actors], axis=0)
            if len(path) > 1 and np.linalg.norm(centroid[:2] - path[0][:2]) < 0.5:
                path = self.paths[group_id] = path[1:]
            self.formation.execute(actors, path[0], centroid, 'solid')

    def get_observation(self, observation, core):
        return {g: np.asarray(v) for g, v in observation.items()}, {}

    def get_done_status(self, observation, core):
        if not self.paths:
            return False
        for group_id, path in self.paths.items():
            centroid = np.mean(observation[group_id], axis=0)
            if np.linalg.norm(centroid[:2] - path[-1][:2]) > self.tolerance:
                return False
        return True

    def compute_reward(self, observation, core):
        return 0.0
