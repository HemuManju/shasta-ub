import os
import psutil
import signal

from .world import World

from .utils import get_initial_positions


def kill_all_servers():
    """Kill all PIDs that start with Carla"""
    processes = [
        p for p in psutil.process_iter() if "carla" in p.name().lower()
    ]
    for process in processes:
        os.kill(process.pid, signal.SIGKILL)


class ShastaCore():
    """
    Class responsible of handling all the different CARLA functionalities,
    such as server-client connecting, actor spawning,
    and getting the sensors data.
    """
    def __init__(self, config, actor_groups: dict = None):
        """Initialize the server and client"""
        self.config = config
        self.actor_groups = actor_groups

        # Verify if the actor groups is a dictionary
        if not isinstance(self.actor_groups, dict):
            raise TypeError('Actor groups should be of type dict')

        self.world = World(config)
        self.map = self.world.get_map()

        self.init_server()

    def init_server(self):
        """Start a server on a random port"""
        pass

    def setup_experiment(self, experiment_config):
        """Initialize the hero and sensors"""

        # Load the environment and setup the map
        self.map._setup(experiment_config)
        read_path = self.map.asset_path + '/environment_collision_free.urdf'
        self.world.load_world_model(read_path)

        # Spawn the actors in thes physics client
        self.spawn_actors()

    def get_world(self):
        """Get the World object from the simulation

        Returns
        -------
        object
            The world object
        """
        return self.world

    def get_map(self):
        """Get the Map object from the simulation

        Returns
        -------
        object
            The map object
        """
        return self.map

    def reset(self):
        """This function resets / spawns the hero vehicle and its sensors"""

        # Reset all the actors
        observations = {}
        for group_id in self.actor_groups:
            # Check if the entry is a list or not
            if not isinstance(self.actor_groups[group_id], list):
                self.actor_groups[group_id] = [self.actor_groups[group_id]]

            obs_from_each_actor = []
            for actor in self.actor_groups[group_id]:
                # Reset the actor and collect the observation
                actor.reset()
                obs_from_each_actor.append(actor.get_observation)

            observations[group_id] = obs_from_each_actor

        return observations

    def spawn_actors(self):
        """Spawns vehicles and walkers, also setting up the Traffic Manager and its parameters"""
        for group_id in self.actor_groups:
            # Check if the entry is a list or not
            if not isinstance(self.actor_groups[group_id], list):
                self.actor_groups[group_id] = [self.actor_groups[group_id]]

            # Spawn the actors
            spawn_point = self.map.get_cartesian_spawn_points()
            positions = get_initial_positions(spawn_point, 10,
                                              len(self.actor_groups[group_id]))
            for actor, position in zip(self.actor_groups[group_id], positions):
                self.world.spawn_actor(actor, position)

    def get_actor_groups(self):
        """Get the actor groups

        Returns
        -------
        dict
            The actor groups as a dict with group id as the key
            list of actors as the value
        """
        return self.actor_groups

    def get_actors_by_group_id(self, group_id):
        """Get a list of actor given by group id

        Parameters
        ----------
        group_id : int
            Group id to be returned

        Returns
        -------
        list
            A list of actor given the group id
        """
        return self.actor_groups[group_id]

    def tick(self):
        """Performs one tick of the simulation, moving all actors, and getting the sensor data"""
        observations = {}

        # Tick once the simulation
        self.world.tick()

        # Collect the raw observation from all the actors in each actor group
        for group in self.actor_groups:
            obs_from_each_actor = [
                actor.get_observation() for actor in self.actor_groups[group]
            ]

            observations[group] = obs_from_each_actor

        return observations

    def close_simulation(self):
        """Close the simulation
        """
        self.world.disconnect()
