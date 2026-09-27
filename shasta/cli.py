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

    gui = sub.add_parser("gui", help="open the human interface to command swarm groups")
    gui.add_argument("--map", default="buffalo-small")
    gui.add_argument("--uav-groups", type=int, default=2)
    gui.add_argument("--ugv-groups", type=int, default=2)
    gui.add_argument("--targets", type=int, default=3)
    gui.add_argument("--time-limit", type=int, default=None, help="mission length in steps")
    gui.add_argument("--seed", type=int, default=None)

    sub.add_parser("maps", help="list the maps that can be found")

    fetch = sub.add_parser("fetch-osm", help="download roads and buildings for an area")
    fetch.add_argument(
        "--bbox", type=float, nargs=4, required=True,
        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
    )
    fetch.add_argument("-o", "--output", required=True, help="output .osm file")

    sub.add_parser("setup-java", help="download a Java runtime for build-map (about 45 MB)")

    build = sub.add_parser("build-map", help="build a SHASTA map from an .osm file")
    build.add_argument("osm", help="input .osm file")
    build.add_argument("--name", required=True, help="name of the new map")
    build.add_argument("--out", default="assets", help="folder that will hold the map")
    build.add_argument("--overwrite", action="store_true")

    args = parser.parse_args(argv)
    try:
        _dispatch(args, parser)
    except (RuntimeError, FileNotFoundError, FileExistsError, ValueError) as exc:
        raise SystemExit(f"error: {exc}")


def _dispatch(args, parser):
    if args.command == "demo":
        from shasta.demo import run_demo

        run_demo(
            gui=args.gui,
            map_name=args.map,
            n_uav=args.uavs,
            n_ugv=args.ugvs,
            steps=args.steps,
        )
    elif args.command == "gui":
        from shasta.demo import run_gui

        run_gui(
            map_name=args.map,
            n_uav_groups=args.uav_groups,
            n_ugv_groups=args.ugv_groups,
            n_targets=args.targets,
            time_limit=args.time_limit,
            seed=args.seed,
        )
    elif args.command == "maps":
        from shasta.assets import list_maps

        print("\n".join(list_maps()))
    elif args.command == "fetch-osm":
        from shasta.preprocessing.build import fetch_osm

        path = fetch_osm(*args.bbox, args.output)
        print(f"Saved {path} ({path.stat().st_size / 1e3:.0f} kB)")
    elif args.command == "setup-java":
        from shasta.preprocessing.osm2world import download_java, find_java

        java = find_java() or download_java()
        print(f"Java ready: {java}")
    elif args.command == "build-map":
        import sys

        from shasta.preprocessing.build import build_map, calibration_error
        from shasta.preprocessing.osm2world import download_java, find_java

        if find_java() is None and sys.stdin.isatty():
            answer = input("Java 11+ is needed to build maps. Download it now (about 45 MB)? [Y/n] ")
            if answer.strip().lower() in ("", "y", "yes"):
                download_java()

        folder = build_map(args.osm, args.name, args.out, overwrite=args.overwrite)
        error = calibration_error(folder / "coordinates.csv")
        print(f"Built map '{args.name}' in {folder} (calibration error {error:.2f} m)")
        print(f"Try it: shasta demo --map {args.name}")
    else:
        parser.print_help()
