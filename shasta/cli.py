import argparse

from shasta import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="shasta", description="SHASTA human-swarm teaming simulator"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    demo = sub.add_parser("demo", help="run a swarm go-to-node demo")
    demo.add_argument("--gui", action="store_true", help="open the pybullet window")
    demo.add_argument("--map", default="buffalo-small")
    demo.add_argument("--uavs", type=int, default=4)
    demo.add_argument("--ugvs", type=int, default=3)
    demo.add_argument("--steps", type=int, default=2000)

    sub.add_parser("maps", help="list the maps that can be found")

    args = parser.parse_args(argv)
    if args.command == "demo":
        from shasta.demo import run_demo

        run_demo(
            gui=args.gui,
            map_name=args.map,
            n_uav=args.uavs,
            n_ugv=args.ugvs,
            steps=args.steps,
        )
    elif args.command == "maps":
        from shasta.assets import list_maps

        print("\n".join(list_maps()))
    else:
        parser.print_help()
