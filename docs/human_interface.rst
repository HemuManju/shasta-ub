===============
Human interface
===============

.. code-block:: console

    $ shasta gui --map buffalo-medium --uav-groups 6 --ugv-groups 3 --targets 3 --seed 1

The window shows a top-down, north-up map. Blue triangles are UAVs, red squares are UGVs, cyan dots are street
nodes, and yellow diamonds are mission targets. Buildings are colour-coded by type (civic, worship, commercial,
garage/industrial, other).

Controls
--------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Action
     - How
   * - Select a group
     - Click its marker, or press ``1``-``9``
   * - Add / remove a group
     - ``Shift`` + click its marker, or ``Shift`` + ``1``-``9``
   * - Select several groups
     - ``Shift`` + drag a box on the map
   * - Select by type
     - ``U`` all UAV groups, ``G`` all UGV groups, ``Ctrl+A`` everything (or the buttons at the top of the side panel)
   * - Pick a target
     - Click near a street node; a white cross marks it
   * - Send the selection
     - ``Enter``, the **Send order** button, or double-click the node
   * - Send every group
     - **Send ALL groups**
   * - Cancel orders
     - **Cancel order** (applies to the selected groups)
   * - Pause / speed
     - ``Space``; ``-`` and ``+``
   * - Zoom / pan / reset
     - Mouse wheel; right-drag; ``R``
   * - 3D camera view
     - ``V`` (a pybullet camera that follows the selected group)

The side panel shows mission progress, the selected group's battery, ammo, distance and ETA (or a summary when
several groups are selected), and an event log. The simulation stops when every target is reached or the time
limit (``--time-limit``) runs out. A group reaches a target when its centre passes within the target radius.

Options
-------

``--map``, ``--uav-groups``, ``--ugv-groups``, ``--targets``, ``--time-limit`` (steps), ``--seed``.

Driving it from Python
----------------------

The GUI is a thin layer over :class:`shasta.interaction.SwarmCommander`, which has no display dependency. Use it
for scripted "humans", AI advisors, or automated experiments:

.. code-block:: python

    from shasta.interaction import Mission, SwarmCommander

    commander = SwarmCommander(env, Mission.random(env.core.get_map(), 3, seed=0))
    commander.select_type('uav')                         # or commander.select(0, add=True)
    commander.send_selected(commander.mission.targets[0])
    while not commander.mission.is_complete():
        commander.update()
    print(commander.events)
