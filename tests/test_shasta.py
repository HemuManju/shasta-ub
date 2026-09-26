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


def test_group_moves_toward_target(env):
    obs, _ = env.reset()
    target = env.experiment.planner.map.get_cartesian_node_position(3)
    before = np.linalg.norm(obs[0].mean(axis=0)[:2] - target[:2])
    env.step({0: 3})
    for _ in range(100):
        obs, *_ = env.step(None)
    after = np.linalg.norm(obs[0].mean(axis=0)[:2] - target[:2])
    assert after < before


def test_demo_cli_help(capsys):
    from shasta.cli import main

    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out
