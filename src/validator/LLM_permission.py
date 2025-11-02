import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".artifact_miner_config.json"

def _load_config():
    """Load the user configuration file if it exists."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def _save_config(config):
    """Save the configuration file to disk."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def request_external_service_permission(service_name: str, data_description: str) -> bool:
    """
    Request user permission before sending data to an external service.

    Args:
        service_name (str): Name of the external service (e.g., "OpenAI API").
        data_description (str): Description of what data will be sent.

    Returns:
        bool: True if user consents, False otherwise.
    """

    config = _load_config()

    # Check if user has already set a preference
    if "external_services" in config and service_name in config["external_services"]:
        return config["external_services"][service_name]

    # Explain implications
    print(f"\n⚠️  Data Privacy Notice for {service_name}")
    print(f"The following data may be sent externally:\n  → {data_description}\n")
    print("By proceeding, you acknowledge that this data may be processed by third-party servers.")
    print("No sensitive personal data should be included unless absolutely necessary.\n")

    choice = input("Do you consent to send this data? (yes/no): ").strip().lower()

    allow = choice in ["yes", "y"]
    print("\n✅ External service allowed.\n" if allow else "🚫 External service disabled. Local fallback will be used.\n")

    # Store the user's decision
    config.setdefault("external_services", {})[service_name] = allow
    _save_config(config)

    return allow
