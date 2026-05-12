"""Configuration management for Q-Caliper."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AppConfig:
    """Application configuration settings."""

    company_name: str = "Q-Caliper"
    author: str = ""
    # Add other persistent settings here if needed

    @classmethod
    def load(cls) -> AppConfig:
        """Load configuration from the user's home directory."""
        config_path = cls._get_config_path()
        if not config_path.exists():
            return cls()

        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        except Exception:
            return cls()

    def save(self) -> None:
        """Save current configuration to the user's home directory."""
        config_path = self._get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, indent=4, ensure_ascii=False)
        except Exception:
            pass

    @staticmethod
    def _get_config_path() -> Path:
        """Get the path to the configuration file."""
        return Path.home() / ".q_caliper" / "config.json"
