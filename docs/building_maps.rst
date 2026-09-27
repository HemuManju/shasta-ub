=====================
Build your own map
=====================

SHASTA runs on real places. You pick an area on `OpenStreetMap <https://www.openstreetmap.org>`_, and SHASTA
turns it into a 3D world (buildings and roads) plus the street graph the vehicles drive on. This takes about
five minutes and three commands:

.. code-block:: console

    $ shasta fetch-osm --bbox 43.000 -78.792 43.006 -78.783 -o campus.osm
    $ shasta build-map campus.osm --name campus
    $ shasta gui --map campus

What you need
-------------

* ``pip install "ihuman-shasta[gui]"`` (see :doc:`installation`)
* **Java 11 or newer**, only for the ``build-map`` step (:ref:`install-java` below)
* An internet connection for the first run. It downloads the map data and a one-time 26 MB tool
  (OSM2World) that converts the map to 3D.

.. _install-java:

Step 0: Install Java 11 or newer
--------------------------------

Check whether you already have it:

.. code-block:: console

    $ java -version

If it prints ``11`` or higher (for example ``openjdk version "17.0.9"``), skip to Step 1. Java 8 is **too old**.
If the command is not found, pick the easiest option:

**Option A: let SHASTA download it (recommended).** No admin rights needed. It downloads a small Java runtime
(about 45 MB) into ``~/.cache/shasta`` and does not touch the rest of your system:

.. code-block:: console

    $ shasta setup-java

``shasta build-map`` also offers to do this for you if Java is missing.

**Option B: install it yourself.**

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - System
     - Command
   * - Any
     - Download a JRE 11 or newer from https://adoptium.net
   * - Conda
     - ``conda install -c conda-forge openjdk``
   * - Ubuntu / Debian
     - ``sudo apt install openjdk-11-jre-headless``
   * - macOS (Homebrew)
     - ``brew install openjdk@11``
   * - Windows
     - ``winget install EclipseAdoptium.Temurin.11.JRE``

Open a new terminal afterwards and run ``java -version`` again. SHASTA looks for Java in its own cache first,
then in ``JAVA_HOME``, then on your ``PATH``, and uses the first one that is version 11 or newer.

Step 1: Get the OpenStreetMap data
----------------------------------

You need an ``.osm`` file for your area. Two ways to get one.

**Option A: from the command line.** Give a bounding box as four numbers, *south west north east*
(latitude and longitude in decimal degrees):

.. code-block:: console

    $ shasta fetch-osm --bbox 43.000 -78.792 43.006 -78.783 -o campus.osm

To find the numbers, open https://www.openstreetmap.org, click **Export**, then **Manually select a different
area** and drag the box. The panel shows the four edges: *north* (top), *west* (left), *east* (right) and *south*
(bottom). Reorder them as ``south west north east``.

**Option B: export by hand.** In the same **Export** panel, press the blue **Export** button to download a
``map.osm`` file. openstreetmap.org refuses areas with too many objects. If it does, choose a smaller area,
or use Option A, which has no such limit.

.. tip::

   Keep the area to a campus or a few blocks, up to about 2 km across. The 3D world and the simulation get
   slower as the area grows. About 0.5 to 1 km works well for a tutorial.

The public data servers are sometimes busy. ``fetch-osm`` tries three servers automatically. If all of them
fail, wait a minute and retry, or use Option B.

Step 2: Build the map
---------------------

.. code-block:: console

    $ shasta build-map campus.osm --name campus

This creates the folder ``./assets/campus`` (use ``--out`` to choose another location). The first run
downloads the OSM2World tool once into ``~/.cache/shasta``. When it finishes you see:

.. code-block:: text

    Built map 'campus' in assets/campus (calibration error 0.00 m)
    Try it: shasta demo --map campus

The folder contains:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - File
     - What it is
   * - ``map.osm``
     - The OpenStreetMap data you gave it. Used to build the street graph and building outlines.
   * - ``meshes/map.obj``, ``map.obj.mtl``
     - The 3D world (buildings, roads, ground) that pybullet loads.
   * - ``coordinates.csv``
     - Matching points that tie map positions (latitude, longitude) to positions in the 3D world.
   * - ``environment_collision_free.urdf``
     - The description pybullet loads. Vehicles fly and drive through the world without colliding with it.

Add ``--overwrite`` to rebuild a map that already exists.

Step 3: Use it
--------------

.. code-block:: console

    $ shasta gui --map campus              # human interface
    $ shasta demo --map campus             # headless demo

From Python, set ``config['experiment']['map_to_use'] = 'campus'``.

SHASTA looks for maps in ``$SHASTA_ASSETS``, then ``./assets`` in the folder you run from, then the maps that
ship with the package. Run ``shasta maps`` to see what it can find. To share a map, send the whole folder
(``assets/campus``). Your colleague puts it in their own ``assets`` folder or sets ``SHASTA_ASSETS`` to its
parent folder.

How it works
------------

1. OSM2World converts the OpenStreetMap buildings and roads into a 3D mesh. Our build of it also writes
   ``coordinates.csv``: sample points listed once in map coordinates (latitude, longitude) and once in
   simulator coordinates (metres).
2. SHASTA fits an affine transform to those points by least squares. This is how a street node from the map
   ends up at the right place in the 3D world. The *calibration error* printed by ``build-map`` is the average
   miss of that fit. It should be well under a metre; a large number means something went wrong with the map.
3. The street graph is built from the roads in ``map.osm`` (motorways down to service roads). Footpaths, plazas,
   steps and building outlines are ignored, so vehicles only route along roads. Change this with
   ``config['experiment']['road_types']``.

Troubleshooting
---------------

``Java 11+ is required to build maps but was not found``
    Run ``shasta setup-java`` or see :ref:`install-java`. Java 8 does not work.

``Could not download OSM2World``
    The one-time tool download failed (no internet, a proxy or a firewall). Download ``osm2world.zip`` from the
    project's GitHub releases (tag ``osm2world-v1``), unzip it, and set ``SHASTA_OSM2WORLD`` to the folder that
    contains ``OSM2WORLD.jar`` and ``lib/``.

``All Overpass servers failed``
    The data servers are busy or blocked. Retry in a minute, or export the area from openstreetmap.org
    (Step 1, option B) and pass that file to ``build-map``.

``No roads ... found``
    The area has no drivable roads (for example a park or a pedestrian-only zone). Choose a different area, or
    include footways with ``road_types``.

``OSM2World did not produce map.obj``
    The area may be empty or too large. The message includes the tool's own output; try a smaller area.

The 3D camera view (``V`` in the GUI) shows only flat ground
    The selected vehicles are outside the built area. The street graph can extend slightly past the edge of the
    3D mesh. Pick a group that is over the middle of the map.

Working offline (for example at a workshop)
    Build the maps beforehand while you are online, then copy the ``assets/<name>`` folders to the other
    machines. Running a map needs no internet and no Java. Only building one does. To keep the tools somewhere
    other than ``~/.cache/shasta``, set ``SHASTA_CACHE``.

Environment variables
---------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Purpose
   * - ``SHASTA_ASSETS``
     - Folder that holds your maps
   * - ``SHASTA_OSM2WORLD``
     - Folder containing ``OSM2WORLD.jar`` and ``lib/`` (skips the download)
   * - ``SHASTA_CACHE``
     - Where the OSM2World tool and the downloaded Java are stored (default ``~/.cache/shasta``)
   * - ``JAVA_HOME``
     - A Java installation to use
