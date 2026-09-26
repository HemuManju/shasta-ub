from pathlib import Path

import yaml

_DEFAULT = Path(__file__).resolve().parent / "data" / "default_config.yml"


def load_config(path=None, **overrides):
    """Load the packaged default config, or ``path``, then apply ``overrides``.

    Top-level keys in ``overrides`` replace the loaded values, e.g.
    ``load_config(headless=True)``. Use ``experiment=...`` to replace the
    experiment section wholesale.
    """
    with open(path or _DEFAULT) as f:
        config = yaml.safe_load(f)
    config.update(overrides)
    return config
