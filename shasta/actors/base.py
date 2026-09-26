import copy
from abc import ABC, abstractmethod


class BaseActor(ABC):
    """Base class for any vehicle that lives in a SHASTA world."""

    def __init__(self, init_pos=None, init_orientation=None):
        self.physics_client = None
        self._loaded = False
        self.states = {}
        self._actor_id = None
        self.init_pos = init_pos
        self.init_orientation = init_orientation
        self.current_pos = copy.deepcopy(init_pos)
        self.desired_pos = copy.deepcopy(init_pos)

    def _load(self):
        """Load the actor into pybullet and return the list of body ids."""
        if self._loaded:
            raise ValueError("Cannot load an actor multiple times.")
        self._loaded = True
        actor_ids = self.load_asset()

        if not isinstance(actor_ids, list):
            actor_ids = [actor_ids]

        self._actor_id = actor_ids[0]
        return actor_ids

    def get_actor_id(self):
        return self._actor_id

    @abstractmethod
    def load_asset(self, *args, **kwargs):
        """Load the model of the actor into the physics client."""

    @abstractmethod
    def reset(self, *args, **kwargs):
        """Reset the actor to its initial state."""

    @abstractmethod
    def get_observation(self, *args, **kwargs):
        """Return the observation of the actor."""

    @abstractmethod
    def apply_action(self, *args, **kwargs):
        """Apply an action to the actor."""

    @abstractmethod
    def destroy(self, *args, **kwargs):
        """Remove the actor from the world."""
