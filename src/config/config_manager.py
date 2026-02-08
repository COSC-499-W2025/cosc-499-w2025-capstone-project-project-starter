"""
config_manager.py
-------------------
SQLite-backed manager responsible for storing user configuration and consent data.

User data now lives in a normalized `user_configurations` table instead of JSON blobs.
Each record keeps: user_id, uploaded zip_file path, external LLM consent flag,
created_at timestamp, and updated_at timestamp (null until the first update).

Typical usage from the repo root:
    docker compose run --rm backend python -m src.config.config_manager --user-id testuser --save --zip-file /tmp/data.zip
    docker compose run --rm backend python -m src.config.config_manager --user-id testuser --load --pretty
    docker compose run --rm backend python -m src.config.config_manager --user-id testuser --update --zip-file /tmp/new.zip --llm-consent yes
"""

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

DB_PATH = "data/app.db"
TABLE_NAME = "user_configurations"


@dataclass
class UserConfig:
    """Simple container used for moving config data between the DB and CLI."""

    user_id: str
    zip_file: str
    llm_consent: bool
    llm_consent_asked: bool
    data_access_consent: bool
    created_at: str
    updated_at: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "zip_file": self.zip_file,
            "llm_consent": self.llm_consent,
            "llm_consent_asked": self.llm_consent_asked,
            "data_access_consent": self.data_access_consent,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UserConfigManager:
    """High-level API for persisting user configuration flags in SQLite."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DB_PATH

    def _ensure_db_directory(self) -> None:
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def init_db(self) -> None:
        """Ensure the user_configurations table exists."""
        self._ensure_db_directory()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    user_id TEXT PRIMARY KEY,
                    zip_file TEXT NOT NULL,
                    llm_consent INTEGER NOT NULL,
                    llm_consent_asked INTEGER NOT NULL DEFAULT 0,
                    data_access_consent INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                );
                """
            )
            # Backfill column if missing in older DBs
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({TABLE_NAME});")}
            if "data_access_consent" not in cols:
                conn.execute(
                    f"ALTER TABLE {TABLE_NAME} ADD COLUMN data_access_consent INTEGER NOT NULL DEFAULT 0;"
                )
            if "llm_consent_asked" not in cols:
                conn.execute(
                    f"ALTER TABLE {TABLE_NAME} ADD COLUMN llm_consent_asked INTEGER NOT NULL DEFAULT 0;"
                )
            conn.commit()

    def _persist_config(self, config: UserConfig) -> bool:
        try:
            self.init_db()
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (user_id, zip_file, llm_consent, llm_consent_asked, data_access_consent, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        zip_file = excluded.zip_file,
                        llm_consent = excluded.llm_consent,
                        llm_consent_asked = excluded.llm_consent_asked,
                        data_access_consent = excluded.data_access_consent,
                        updated_at = excluded.updated_at;
                    """,
                    (
                        config.user_id,
                        config.zip_file,
                        int(config.llm_consent),
                        int(config.llm_consent_asked),
                        int(config.data_access_consent),
                        config.created_at,
                        config.updated_at,
                    ),
                )
                conn.commit()
            return True
        except Exception as exc:  # pragma: no cover - defensive logging only
            print(f"Error writing config to DB: {exc}")
            return False

    def create_config(
        self,
        user_id: str,
        zip_file: str,
        llm_consent: bool,
        llm_consent_asked: bool = False,
        data_access_consent: bool = False,
    ) -> bool:
        """Insert a brand-new config row for the given user."""
        if self.load_config(user_id, silent=True):
            print(f"Configuration already exists for user_id={user_id}; use --update instead.")
            return False

        timestamp = datetime.now(timezone.utc).isoformat()
        config = UserConfig(
            user_id=user_id,
            zip_file=zip_file,
            llm_consent=llm_consent,
            llm_consent_asked=llm_consent_asked,
            data_access_consent=data_access_consent,
            created_at=timestamp,
            updated_at=None,
        )
        return self._persist_config(config)

    def update_config(
        self,
        user_id: str,
        zip_file: Optional[str] = None,
        llm_consent: Optional[bool] = None,
        llm_consent_asked: Optional[bool] = None,
        data_access_consent: Optional[bool] = None,
    ) -> bool:
        """Update an existing config row."""
        existing = self.load_config(user_id, silent=True)
        if not existing:
            print(f"No configuration found for user_id={user_id}")
            return False

        if zip_file is not None:
            existing.zip_file = zip_file
        if llm_consent is not None:
            existing.llm_consent = llm_consent
        if llm_consent_asked is not None:
            existing.llm_consent_asked = llm_consent_asked
        if data_access_consent is not None:
            existing.data_access_consent = data_access_consent

        existing.updated_at = datetime.now(timezone.utc).isoformat()
        return self._persist_config(existing)

    def load_config(self, user_id: str, silent: bool = False) -> Optional[UserConfig]:
        """Fetch a config object for the given user."""
        try:
            self.init_db()
            with sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    f"""
                    SELECT user_id, zip_file, llm_consent, llm_consent_asked, data_access_consent, created_at, updated_at
                    FROM {TABLE_NAME}
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()
        except Exception as exc:  # pragma: no cover - defensive logging only
            print(f"Error loading config from DB: {exc}")
            return None

        if not row:
            if not silent:
                print(f"No configuration found for user_id={user_id}")
            return None

        return UserConfig(
            user_id=row[0],
            zip_file=row[1],
            llm_consent=bool(row[2]),
            llm_consent_asked=bool(row[3]),
            data_access_consent=bool(row[4]),
            created_at=row[5],
            updated_at=row[6],
        )


def init_db() -> None:
    UserConfigManager().init_db()


def save_config_to_db(config: Dict[str, Any], user_id: str) -> bool:
    """Helper used by legacy callers to store config data."""
    zip_file = config.get("zip_file")
    if not zip_file:
        raise ValueError("zip_file is required to save a configuration")

    llm_consent = bool(config.get("llm_consent", False))
    llm_consent_asked = bool(config.get("llm_consent_asked", False))
    data_access_consent = bool(config.get("data_access_consent", False))

    manager = UserConfigManager()
    if manager.load_config(user_id, silent=True):
        return manager.update_config(
            user_id,
            zip_file=zip_file,
            llm_consent=llm_consent,
            llm_consent_asked=llm_consent_asked,
            data_access_consent=data_access_consent,
        )

    return manager.create_config(
        user_id,
        zip_file=zip_file,
        llm_consent=llm_consent,
        llm_consent_asked=llm_consent_asked,
        data_access_consent=data_access_consent,
    )


def load_config_from_db(user_id: str) -> Dict[str, Any]:
    config = UserConfigManager().load_config(user_id)
    return config.as_dict() if config else {}


def update_config_in_db(
    user_id: str,
    zip_file: Optional[str] = None,
    llm_consent: Optional[bool] = None,
    llm_consent_asked: Optional[bool] = None,
    data_access_consent: Optional[bool] = None,
) -> bool:
    return UserConfigManager().update_config(
        user_id,
        zip_file=zip_file,
        llm_consent=llm_consent,
        llm_consent_asked=llm_consent_asked,
        data_access_consent=data_access_consent,
    )


def _parse_bool_arg(raw_value: Optional[str], parser) -> Optional[bool]:
    """Convert CLI string input into a boolean when provided."""
    if raw_value is None:
        return None

    normalized = raw_value.strip().lower()
    truthy = {"y", "yes", "true", "t", "1"}
    falsy = {"n", "no", "false", "f", "0"}

    if normalized in truthy:
        return True
    if normalized in falsy:
        return False
    parser.error("--llm-consent accepts yes/no values.")
    return None


def _prompt_yes_no(message: str, default: Optional[bool] = None) -> bool:
    """Prompt the user for a Y/N answer, respecting a default when provided."""
    if default is None:
        prompt = f"{message} (Y/N): "
    else:
        prompt = f"{message} [{'Y' if default else 'N'}]: "

    while True:
        response = input(prompt).strip().lower()
        if not response and default is not None:
            return default
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please respond with Y or N.")


def _request_zip_file(args, current: Optional[str]) -> str:
    """Determine or prompt for the zip file path to store."""
    if args.zip_file:
        return args.zip_file

    while True:
        suffix = f" [{current}]" if current else ""
        response = input(f"Enter the path to the zip file to analyze{suffix}: ").strip()
        if response:
            return response
        if current:
            return current
        print("Zip file path is required.")


def _request_llm_consent(default: Optional[bool] = None) -> bool:
    """Explain privacy implications and capture the LLM consent decision."""
    print(
        "Privacy notice: enabling the external LLM service may send derived summaries "
        "to a hosted API. No raw files leave the machine, but continue only if you are comfortable "
        "with that data flow. Local-only analysis is available if you opt out."
    )
    consent = _prompt_yes_no(
        "Do you consent to using the external LLM service?",
        default=default,
    )

    if consent:
        print("User is opting into the external LLM service.")
        return True

    confirm_opt_out = _prompt_yes_no(
        "Confirm you want to opt-out of external LLM services and use the local analysis path?",
        default=True,
    )
    if confirm_opt_out:
        print("User is opting out of external LLM services. Local-only analysis will be used.")
        return False

    print("Opt-out cancelled. User is opting into the external LLM service.")
    return True


def _print_config(config: UserConfig, pretty: bool) -> None:
    indent = 2 if pretty else None
    print(json.dumps(config.as_dict(), indent=indent))


def run_cli() -> None:  # pragma: no cover - CLI utility wiring
    """Command-line interface for saving, loading, and updating configs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage user consent/configuration data in SQLite."
    )
    parser.add_argument("--user-id", required=True, help="User identifier.")
    parser.add_argument("--zip-file", help="Path to the zip file to store or update.")
    parser.add_argument(
        "--llm-consent",
        help="Provide yes/no to override the interactive LLM consent prompt."
    )
    parser.add_argument("--save", action="store_true", help="Create a new configuration.")
    parser.add_argument("--load", action="store_true", help="Load and print an existing configuration.")
    parser.add_argument("--update", action="store_true", help="Update an existing configuration.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output when loading.")
    args = parser.parse_args()

    llm_arg = _parse_bool_arg(args.llm_consent, parser)
    operations = [args.save, args.load, args.update]
    if sum(1 for op in operations if op) != 1:
        parser.error("Select exactly one action: --save, --load, or --update.")

    manager = UserConfigManager()

    if args.save:
        zip_file = _request_zip_file(args, current=None)
        llm_consent = llm_arg if llm_arg is not None else _request_llm_consent(default=None)
        if manager.create_config(args.user_id, zip_file, llm_consent):
            print(f"Config saved to DB for user_id={args.user_id}")
        return

    if args.load:
        config = manager.load_config(args.user_id)
        if not config:
            return
        print(f"Config found for user_id={args.user_id}")
        _print_config(config, pretty=args.pretty)
        return

    # Update flow
    existing = manager.load_config(args.user_id)
    if not existing:
        return

    zip_file = _request_zip_file(args, current=existing.zip_file)
    llm_consent = llm_arg if llm_arg is not None else _request_llm_consent(default=existing.llm_consent)

    if manager.update_config(
        args.user_id,
        zip_file=zip_file,
        llm_consent=llm_consent,
    ):
        print(f"Config updated for user_id={args.user_id}")
        return


if __name__ == "__main__":
    run_cli()
