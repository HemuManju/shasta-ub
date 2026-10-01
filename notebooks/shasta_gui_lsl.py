"""Run on the LAPTOP: the normal SHASTA human interface, plus an LSL marker stream of the human's orders.

    pip install "ihuman-shasta[gui]" pylsl
    python shasta_gui_lsl.py --map buffalo-small

Start ``tobii_to_lsl.py`` and LabRecorder first. LabRecorder will then record two streams into one XDF
file: ``Markers`` (this script) and ``Gaze`` (the eye tracker). Upload the file and open it in notebook 1
(step 10). Run with a real window, i.e. NOT on the hub.
"""

import argparse
import random

import numpy as np

from shasta.actors import UAV, UGV
from shasta.config import load_config
from shasta.env import ShastaEnv
from shasta.experiments import GoToNodeExperiment
from shasta.gui import ShastaGUI
from shasta.interaction import Mission, SwarmCommander

from lsl_tools import MarkerOutlet, attach_markers, attach_order_markers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", default="buffalo-small")
    parser.add_argument("--targets", type=int, default=3)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
        np.random.seed(args.seed)
    config = load_config(headless=True)
    config["experiment"] = {"map_to_use": args.map, "type": GoToNodeExperiment}
    groups = {0: [UAV() for _ in range(4)], 1: [UAV() for _ in range(4)],
              2: [UGV() for _ in range(3)], 3: [UGV() for _ in range(3)]}

    env = ShastaEnv(config, groups)
    mission = Mission.random(env.core.get_map(), args.targets, seed=args.seed)
    commander = SwarmCommander(env, mission)
    gui = ShastaGUI(commander)

    markers = MarkerOutlet("SHASTA-Events")
    attach_markers(commander, markers)
    attach_order_markers(commander, markers, gui.view)
    markers.push("session_start", screen=list(gui.size), map_rect=list(gui.map_rect),
                 targets=mission.targets)
    gui.run()
    markers.push("session_end", score=mission.score)
    env.close()


if __name__ == "__main__":
    main()
