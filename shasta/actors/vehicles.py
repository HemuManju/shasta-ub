import copy

import numpy as np

from shasta.assets import get_asset_path

from .base import BaseActor


class _UxV(BaseActor):
    """A point-mass vehicle moved by position commands through a fixed constraint."""

    type = None
    model = None
    color = None
    altitude = None

    def __init__(self, config=None, init_pos=None, init_orientation=None):
        super().__init__(init_pos, init_orientation)
        self.vehicle_id = 0
        self.platoon_id = 0
        self.idle = True
        self.ammo = 100
        self.battery = 100
        self.functional = True
        self.speed = 2.5
        self.search_speed = 0.25

    def load_asset(self):
        if self.init_orientation is None:
            self.init_orientation = self.physics_client.getQuaternionFromEuler(
                [0, 0, np.pi / 2]
            )

        self.object = self.physics_client.loadURDF(
            get_asset_path('vehicles', self.model),
            self.init_pos,
            self.init_orientation,
            flags=self.physics_client.URDF_USE_MATERIAL_COLORS_FROM_MTL,
        )
        self.constraint = self.physics_client.createConstraint(
            self.object,
            -1,
            -1,
            -1,
            self.physics_client.JOINT_FIXED,
            [0, 0, 0],
            [0, 0, 0],
            self.init_pos,
        )
        self.physics_client.changeVisualShape(self.object, -1, rgbaColor=self.color)
        self.current_pos = copy.deepcopy(self.init_pos)
        self.desired_pos = copy.deepcopy(self.init_pos)
        return self.object

    def get_pos_and_orientation(self):
        pos, rot = self.physics_client.getBasePositionAndOrientation(self.object)
        euler = self.physics_client.getEulerFromQuaternion(rot)
        return np.array(pos), euler

    def reset(self):
        self.physics_client.changeConstraint(self.constraint, self.init_pos)
        self.current_pos = copy.deepcopy(self.init_pos)
        self.desired_pos = copy.deepcopy(self.init_pos)

    def get_observation(self):
        pos, _ = self.get_pos_and_orientation()
        return pos

    def apply_action(self, position):
        """Move the vehicle to ``position`` (z is fixed by vehicle type)."""
        self.current_pos, _ = self.get_pos_and_orientation()
        position[2] = self.altitude
        self.physics_client.changeConstraint(self.constraint, position)

    def destroy(self):
        if self.functional:
            self.physics_client.removeBody(self.object)
        self.functional = False


class UAV(_UxV):
    """Unmanned aerial vehicle (blue)."""

    type = 'uav'
    model = 'arial_vehicle_abstract.urdf'
    color = [0, 0, 1, 1]
    altitude = 10.0


class UGV(_UxV):
    """Unmanned ground vehicle (red)."""

    type = 'ugv'
    model = 'ground_vehicle_abstract.urdf'
    color = [1, 0, 0, 1]
    altitude = 0.5
