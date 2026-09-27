SHASTA
======

**S**\ imulator for **H**\ uman-Autonomy and **S**\ warm **T**\ eaming **A**\ pplications.

SHASTA is a `pybullet <https://pybullet.org>`_ simulator for studying human-swarm interaction on real
city maps built from `OpenStreetMap <https://www.openstreetmap.org>`_. Swarms of aerial (UAV) and ground
(UGV) vehicles move in formation along the street network, and a human, a scripted policy or an RL agent
commands them through a Gymnasium interface or the built-in GUI.

.. code-block:: console

    $ pip install "ihuman-shasta[gui]"
    $ shasta gui

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   human_interface
   building_maps
   contributing

Indices and tables
==================
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
