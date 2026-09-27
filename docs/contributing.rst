============
Contributing
============

Bug reports and pull requests are welcome at https://github.com/HemuManju/shasta-ub.

.. code-block:: console

    $ git clone https://github.com/HemuManju/shasta-ub.git
    $ cd shasta-ub
    $ pip install -e ".[test,gui]"
    $ pytest

The GUI tests run without a display (they set ``SDL_VIDEODRIVER=dummy``). The map-building test is skipped
unless Java and the OSM2World tool are available.
