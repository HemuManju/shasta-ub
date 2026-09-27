=====
Usage
=====

Command line
------------

.. code-block:: console

    $ shasta gui                       # human interface
    $ shasta demo                      # headless demo
    $ shasta demo --gui                # demo in the pybullet 3D window
    $ shasta maps                      # list the maps that can be found
    $ shasta fetch-osm --bbox S W N E -o area.osm   # see building_maps
    $ shasta build-map area.osm --name myarea
    $ shasta setup-java                # download Java for build-map

Python
------

.. code-block:: python

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

    # Order both groups to map-graph node 5; they plan a route and move in formation
    obs, reward, terminated, truncated, info = env.step({0: 5, 1: 5})
    while not terminated:
        obs, reward, terminated, truncated, info = env.step(None)   # None = keep going
    env.close()

Map nodes are the intersections of the OpenStreetMap street graph. Only roads are used for routing (motorway
down to service roads); footpaths, plazas, steps and building outlines are ignored. Set
``config['experiment']['road_types']`` to change the list. ``env.core.get_map().get_node_graph()`` gives the
graph and ``get_cartesian_node_position(i)`` gives the simulator coordinates of node ``i``.

To use another map, set ``config['experiment']['map_to_use'] = 'myarea'``.

Your own experiment
-------------------

Subclass :class:`shasta.base_experiment.BaseExperiment` and implement ``apply_actions``, ``get_observation``,
``get_done_status`` and ``compute_reward``. ``shasta/experiments.py`` is a short, complete example. Custom
vehicles subclass :class:`shasta.actors.BaseActor`. Reusable swarm behaviours are in ``shasta.primitives``
(``Formation``, ``PathPlanning``).
