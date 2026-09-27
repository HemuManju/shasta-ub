"""Human-facing control layer: commands, status, events and mission scoring.

``SwarmCommander`` is what a GUI, a scripted "human" or an AI advisor talks to.
It has no display dependency, so the same logic is used (and tested) headlessly.
"""

from dataclasses import dataclass, field

import numpy as np

from shasta.experiments import GoToNodeExperiment


@dataclass
class Mission:
    """Target map nodes that groups must reach, with an optional time limit.

    A group counts as reaching a target when its centroid passes within ``radius``
    metres. The commander stops advancing the simulation once every target is
    reached or the time limit is hit.
    """

    targets: list
    radius: float = 12.0
    time_limit: int = None
    reached: dict = field(default_factory=dict)

    @classmethod
    def random(cls, world_map, n_targets=3, seed=None, **kwargs):
        rng = np.random.default_rng(seed)
        nodes = list(world_map.get_node_graph().nodes)
        targets = [int(n) for n in rng.choice(nodes, size=n_targets, replace=False)]
        return cls(targets=targets, **kwargs)

    @property
    def score(self):
        return len(self.reached)

    def is_complete(self):
        return self.score == len(self.targets)

    def is_over(self, step):
        return self.is_complete() or (
            self.time_limit is not None and step >= self.time_limit
        )


class SwarmCommander:
    """Select groups, order them to map nodes, run the simulation, read status."""

    def __init__(self, env, mission=None, steps_per_update=1):
        if not isinstance(env.experiment, GoToNodeExperiment):
            raise TypeError("SwarmCommander needs an env built on GoToNodeExperiment")
        self.env = env
        self.map = env.core.get_map()
        self.groups = env.core.get_actor_groups()
        self.mission = mission
        self.steps_per_update = steps_per_update
        self.selection = [next(iter(self.groups))]
        self.paused = False
        self.step_count = 0
        self.events = []
        self.orders = {}
        self._arrived = set()
        self.positions = {g: self._positions(g) for g in self.groups}

    def log(self, text):
        self.events.append((self.step_count, text))

    def _positions(self, group_id):
        return np.array(
            [a.get_pos_and_orientation()[0] for a in self.groups[group_id]]
        )

    @property
    def selected(self):
        """The primary group: the most recently selected one."""
        return self.selection[-1]

    def select(self, group_id, add=False):
        """Select ``group_id`` alone, or with ``add=True`` toggle it in the current selection."""
        if group_id not in self.groups:
            raise KeyError(f"Unknown group {group_id}")
        if not add:
            self.selection = [group_id]
        elif group_id in self.selection:
            if len(self.selection) > 1:
                self.selection.remove(group_id)
        else:
            self.selection.append(group_id)

    def select_many(self, group_ids, add=False):
        """Select several groups at once (replacing the selection unless ``add``)."""
        ids = [g for g in group_ids if g in self.groups]
        if not ids:
            return
        base = [g for g in self.selection if add and g not in ids]
        self.selection = base + ids

    def select_type(self, kind=None):
        """Select every group of a vehicle type ('uav' or 'ugv'), or all groups if None."""
        self.select_many(
            [g for g, actors in self.groups.items() if kind is None or actors[0].type == kind]
        )

    def node_position(self, node):
        return np.asarray(self.map.get_cartesian_node_position(node))[:2]

    def nearest_node(self, xy):
        """Map node closest to a simulator (x, y) point."""
        nodes = list(self.map.get_node_graph().nodes)
        coords = np.array([self.node_position(n) for n in nodes])
        return int(nodes[int(np.argmin(np.linalg.norm(coords - xy, axis=1)))])

    def _order(self, group_id, node):
        self.env.experiment.set_target(group_id, int(node))
        self.orders[group_id] = int(node)
        self._arrived.discard(group_id)

    def _cancel(self, group_id):
        self.env.experiment.paths.pop(group_id, None)
        self.orders.pop(group_id, None)
        self._arrived.discard(group_id)

    @staticmethod
    def _names(group_ids):
        return ", ".join(str(g) for g in group_ids)

    def send(self, group_id, node):
        """Order ``group_id`` to travel to ``node`` in formation."""
        self._order(group_id, node)
        self.log(f"Group {group_id} ordered to node {int(node)}")

    def send_groups(self, group_ids, node):
        """Order several groups to the same node (one log line)."""
        group_ids = list(group_ids)
        for group_id in group_ids:
            self._order(group_id, node)
        label = "Group" if len(group_ids) == 1 else "Groups"
        self.log(f"{label} {self._names(group_ids)} ordered to node {int(node)}")

    def send_selected(self, node):
        self.send_groups(list(self.selection), node)

    def send_all(self, node):
        self.send_groups(list(self.groups), node)

    def cancel(self, group_id):
        self._cancel(group_id)
        self.log(f"Group {group_id} order cancelled")

    def cancel_selected(self):
        for group_id in self.selection:
            self._cancel(group_id)
        label = "Group" if len(self.selection) == 1 else "Groups"
        self.log(f"{label} {self._names(self.selection)} order cancelled")

    def toggle_pause(self):
        self.paused = not self.paused
        self.log("Paused" if self.paused else "Resumed")

    def path(self, group_id):
        """Remaining route of a group as an (n, 2) array, or None."""
        path = self.env.experiment.paths.get(group_id)
        return None if path is None else np.asarray(path)[:, :2]

    def update(self):
        """Advance the simulation (unless paused) and refresh derived state."""
        if self.paused or (self.mission and self.mission.is_over(self.step_count)):
            return
        for _ in range(self.steps_per_update):
            self.env.step(None)
            self.step_count += 1
        self.positions = {g: self._positions(g) for g in self.groups}
        self._check_arrivals()

    def _check_arrivals(self):
        for group_id, node in self.orders.items():
            if group_id in self._arrived:
                continue
            centroid = self.positions[group_id].mean(axis=0)[:2]
            if np.linalg.norm(centroid - self.node_position(node)) <= self.env.experiment.tolerance:
                self._arrived.add(group_id)
                self.log(f"Group {group_id} arrived at node {node}")
        if self.mission:
            for target in self.mission.targets:
                if target in self.mission.reached:
                    continue
                for group_id, positions in self.positions.items():
                    centroid = positions.mean(axis=0)[:2]
                    if np.linalg.norm(centroid - self.node_position(target)) <= self.mission.radius:
                        self.mission.reached[target] = group_id
                        self.log(f"Target {target} reached by group {group_id}")
                        break
            if self.mission.is_complete():
                self.log(f"Mission complete in {self.step_count} steps")

    def status(self, group_id):
        actors = self.groups[group_id]
        positions = self.positions[group_id]
        centroid = positions.mean(axis=0)[:2]
        target = self.orders.get(group_id)
        distance = eta = None
        if target is not None:
            distance = float(np.linalg.norm(centroid - self.node_position(target)))
            eta = distance / max(actors[0].speed, 1e-6)
        return {
            "group": group_id,
            "type": actors[0].type,
            "size": len(actors),
            "centroid": centroid,
            "battery": float(np.mean([a.battery for a in actors])),
            "ammo": float(np.mean([a.ammo for a in actors])),
            "target": target,
            "distance": distance,
            "eta": eta,
            "arrived": group_id in self._arrived,
        }
