============
Installation
============

Requirements
------------

* Python 3.9 or newer
* ``pip``

Install
-------

.. code-block:: console

    $ pip install "ihuman-shasta[gui]"

The PyPI package is called ``ihuman-shasta``; the Python package you import is ``shasta``.
The ``[gui]`` extra adds the human interface (``pygame-ce`` and ``pygame_gui``). Without it you still get the
simulator, the headless demo and the Python API.

Check that it works:

.. code-block:: console

    $ shasta demo      # headless, prints swarm progress
    $ shasta gui       # opens the human interface

.. note::

   Java is **not** needed to run SHASTA. It is only needed to build your own maps, see
   :doc:`building_maps`.

From source
-----------

.. code-block:: console

    $ git clone https://github.com/HemuManju/shasta-ub.git
    $ cd shasta-ub
    $ pip install -e ".[test,gui]"
    $ pytest

Maps
----

The package ships with the small ``buffalo-small`` map. Larger maps (Buffalo medium and large, Chicago,
New York, San Jose and others) are in the ``assets/`` folder of the repository. Use them by running from
the repository root, or point ``SHASTA_ASSETS`` at that folder:

.. code-block:: console

    $ export SHASTA_ASSETS=/path/to/shasta-ub/assets
    $ shasta gui --map buffalo-medium

Or create a map of any place yourself: :doc:`building_maps`.
