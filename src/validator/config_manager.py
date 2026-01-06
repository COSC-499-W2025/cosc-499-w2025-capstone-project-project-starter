import json
import os

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),  # project root
    "config.json"
)

def load_config(config_path: str = DEFAULT_CONFIG_PATH):
    """Load configuration JSON. Auto-creates file if missing."""
    if not os.path.exists(config_path):
        # initialize blank config
        with open(config_path, "w") as f:
            json.dump({}, f)

    with open(config_path, "r") as f:
        return json.load(f)


def save_config(config: dict, config_path: str = DEFAULT_CONFIG_PATH):
    """Write updated config back to disk."""
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def get_config_value(config: dict, key: str):
    return config.get(key, None)


def set_config_value(config: dict, key: str, value):
    config[key] = value
    save_config(config)
