import random

import numpy as np
import pytest

from shasta import __version__
from shasta.actors import UAV, UGV
from shasta.assets import get_asset_path, list_maps
from shasta.config import load_config
from shasta.env import ShastaEnv
from shasta.experiments import GoToNodeExperiment


def test_version():
    assert __version__


def test_bundled_assets_found_from_any_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SHASTA_ASSETS", raising=False)
    assert 'buffalo-small' in list_maps()
    assert get_asset_path('vehicles', 'arial_vehicle_abstract.urdf')


def test_missing_asset_message():
    with pytest.raises(FileNotFoundError, match="SHASTA_ASSETS"):
        get_asset_path('no-such-map')


@pytest.fixture
def env():
    random.seed(0)
    np.random.seed(0)
    config = load_config(headless=True)
    config['experiment']['type'] = GoToNodeExperiment
    groups = {0: [UAV() for _ in range(3)], 1: [UGV() for _ in range(2)]}
    env = ShastaEnv(config, groups)
    yield env
    env.close()


def test_reset_and_step_follow_gymnasium_api(env):
    obs, info = env.reset()
    assert obs[0].shape == (3, 3) and obs[1].shape == (2, 3)

    obs, reward, terminated, truncated, info = env.step({0: 3})
    assert isinstance(terminated, bool) and truncated is False


def _route_length_left(env, group_id):
    centroid = env.core.get_actor_groups()[group_id]
    centroid = np.mean([a.get_pos_and_orientation()[0] for a in centroid], axis=0)[:2]
    points = np.vstack([centroid, env.experiment.paths[group_id][:, :2]])
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def test_group_follows_its_route(env):
    env.reset()
    env.step({0: 3})
    before = _route_length_left(env, 0)
    for _ in range(100):
        env.step(None)
    assert _route_length_left(env, 0) < before


def test_demo_cli_help(capsys):
    from shasta.cli import main

    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out


# ---- human interaction layer ----------------------------------------------------

from shasta.interaction import Mission, SwarmCommander  # noqa: E402


@pytest.fixture
def commander(env):
    mission = Mission.random(env.core.get_map(), 2, seed=1)
    return SwarmCommander(env, mission, steps_per_update=5)


def test_commander_sends_group_and_reports_arrival(commander):
    node = commander.mission.targets[0]
    commander.mission = Mission(targets=[node], radius=1.0)
    commander.send(0, node)
    assert commander.status(0)['target'] == node
    for _ in range(600):
        commander.update()
        if commander.status(0)['arrived']:
            break
    assert commander.status(0)['arrived']
    assert any('arrived' in text for _, text in commander.events)


def test_pause_freezes_the_simulation(commander):
    commander.send(0, commander.mission.targets[0])
    commander.toggle_pause()
    before = commander.positions[0].copy()
    for _ in range(5):
        commander.update()
    assert commander.step_count == 0
    assert np.allclose(before, commander.positions[0])


def test_cancel_removes_the_order(commander):
    commander.send(1, commander.mission.targets[0])
    commander.cancel(1)
    assert commander.status(1)['target'] is None
    assert commander.path(1) is None


def test_vehicles_use_battery_while_moving(commander):
    node = commander.mission.targets[0]
    commander.mission = None
    commander.send(0, node)
    for _ in range(40):
        commander.update()
    assert commander.status(0)['battery'] < 100


def test_mission_time_limit_stops_simulation(env):
    commander = SwarmCommander(env, Mission(targets=[0], time_limit=10), steps_per_update=5)
    for _ in range(10):
        commander.update()
    assert commander.step_count == 10


# ---- GUI (headless via SDL dummy driver) ----------------------------------------


@pytest.fixture
def gui(commander, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")
    pytest.importorskip("pygame_gui")
    from shasta.gui import ShastaGUI

    app = ShastaGUI(commander, size=(1000, 700))
    yield app
    pygame.quit()


def _click(pygame, pos, button=1):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=button))


def _key(pygame, key):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))


def test_gui_click_then_enter_sends_selected_group(gui):
    import pygame

    node = gui.commander.mission.targets[0]
    screen_pos = gui.view.to_screen(gui.commander.node_position(node))[0]
    _click(pygame, tuple(screen_pos.astype(int)))
    gui.step()
    assert gui.pending == node
    _key(pygame, pygame.K_RETURN)
    gui.step()
    assert gui.commander.status(gui.commander.selected)['target'] == node


def test_gui_click_on_group_marker_selects_it(gui):
    import pygame

    target_group = 1
    marker = gui.view.to_screen(gui.commander.status(target_group)['centroid'])[0]
    _click(pygame, tuple(marker.astype(int)))
    gui.step()
    assert gui.commander.selected == target_group


def test_gui_keyboard_shortcuts(gui):
    import pygame

    _key(pygame, pygame.K_2)
    _key(pygame, pygame.K_SPACE)
    gui.step()
    assert gui.commander.selected == 1
    assert gui.commander.paused


def test_gui_zoom_keeps_point_under_cursor(gui):
    point = (300, 300)
    before = gui.view.to_world(*point)
    gui.view.zoom_at(point, 2.0)
    assert np.allclose(before, gui.view.to_world(*point))


def test_gui_runs_frames_and_camera_inset(gui):
    gui.toggle_camera()
    gui.run(max_frames=12)
    assert gui.commander.step_count > 0
    assert gui.camera.surface is not None


# ---- map building ----------------------------------------------------------------


def test_build_map_from_osm(tmp_path):
    import shutil

    from shasta.preprocessing.build import build_map, calibration_error
    from shasta.preprocessing.osm2world import find_osm2world

    if find_osm2world() is None or shutil.which("java") is None:
        pytest.skip("needs Java and the OSM2World jar")
    folder = build_map(get_asset_path('buffalo-small', 'map.osm'), 'rebuilt', tmp_path)
    assert (folder / 'coordinates.csv').exists()
    assert (folder / 'meshes' / 'map.obj').exists()
    assert (folder / 'environment_collision_free.urdf').exists()
    assert calibration_error(folder / 'coordinates.csv') < 1.0


def test_building_categories():
    from shasta.preprocessing.utils import building_category

    assert building_category('yes', 'courthouse') == 'civic'
    assert building_category('office') == 'commercial'
    assert building_category('garage', None) == 'industrial'
    assert building_category('yes', None) == 'other'
    assert building_category(None, None) == 'other'


def test_map_reports_a_category_for_every_footprint():
    from shasta.map import Map

    world_map = Map()
    world_map.setup({'map_to_use': 'buffalo-small'})
    footprints = world_map.get_building_footprints()
    categories = world_map.get_building_categories()
    assert footprints and len(footprints) == len(categories)
    assert 'civic' in categories


# ---- multi-selection -------------------------------------------------------------


def test_commander_multi_select_and_send(commander):
    commander.select(0)
    commander.select(1, add=True)
    assert commander.selection == [0, 1] and commander.selected == 1
    commander.select(1, add=True)  # toggles off
    assert commander.selection == [0]
    commander.select(0, add=True)  # never empties the selection
    assert commander.selection == [0]
    commander.select_type('uav')
    assert commander.selection == [0]
    commander.select_type(None)
    assert set(commander.selection) == {0, 1}
    node = commander.mission.targets[0]
    commander.send_selected(node)
    assert commander.status(0)['target'] == node and commander.status(1)['target'] == node
    commander.cancel_selected()
    assert commander.status(0)['target'] is None and commander.status(1)['target'] is None


def test_gui_shift_click_adds_groups(gui, monkeypatch):
    import pygame

    monkeypatch.setattr(gui, '_shift', lambda: True)
    for group_id in (0, 1):
        marker = gui.view.to_screen(gui.commander.status(group_id)['centroid'])[0]
        _click(pygame, tuple(marker.astype(int)))
        gui.step()
    assert set(gui.commander.selection) == {0, 1}


def test_gui_shift_drag_box_selects_groups_inside(gui, monkeypatch):
    import pygame

    monkeypatch.setattr(gui, '_shift', lambda: True)
    points = np.array([gui.view.to_screen(gui.commander.status(g)['centroid'])[0] for g in (0, 1)])
    low, high = points.min(axis=0) - 15, points.max(axis=0) + 15
    _click(pygame, tuple(low.astype(int)))
    gui.step()
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=tuple(high.astype(int)), rel=(0, 0), buttons=(1, 0, 0)))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=tuple(high.astype(int)), button=1))
    gui.step()
    assert {0, 1} <= set(gui.commander.selection)


def test_gui_send_goes_to_every_selected_group(gui):
    import pygame

    _key(pygame, pygame.K_u)
    gui.step()
    gui.pending = gui.commander.mission.targets[0]
    gui.send_pending()
    for group_id in gui.commander.selection:
        assert gui.commander.status(group_id)['target'] == gui.pending


def test_actors_in_a_group_spawn_at_distinct_positions():
    from shasta.utils import get_initial_positions

    positions = np.array(get_initial_positions([0.0, 0.0], 10, 4))
    assert len(np.unique(positions.round(6), axis=0)) == 4


def test_route_graph_uses_only_roads():
    from shasta.map import ROAD_TYPES, Map

    world_map = Map()
    world_map.setup({'map_to_use': 'buffalo-medium'})
    graph = world_map.get_node_graph()
    assert graph.number_of_edges() > 0
    for _, _, data in graph.edges(data=True):
        highway = data.get('highway')
        highway = highway if isinstance(highway, list) else [highway]
        assert any(h in ROAD_TYPES for h in highway), data


def test_missing_java_error_explains_how_to_fix(monkeypatch):
    from shasta.preprocessing import osm2world

    monkeypatch.setattr(osm2world, "find_java", lambda minimum=11: None)
    with pytest.raises(RuntimeError, match="shasta setup-java"):
        osm2world.check_java()


def test_java_version_is_parsed(monkeypatch):
    from shasta.preprocessing import osm2world

    class Result:
        stderr = 'openjdk version "17.0.9" 2023-10-17'

    monkeypatch.setattr(osm2world.subprocess, "run", lambda *a, **k: Result())
    assert osm2world._java_major("java") == 17
    Result.stderr = 'java version "1.8.0_361"'
    assert osm2world._java_major("java") == 1
