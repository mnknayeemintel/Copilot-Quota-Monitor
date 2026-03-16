"""Configuration management for Copilot Quota Monitor."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List


def _default_config_dir() -> Path:
    """Return the platform-specific config directory."""
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "copilot-quota-monitor"
    return Path.home() / ".config" / "copilot-quota-monitor"


@dataclass
class Settings:
    """User-configurable settings, equivalent to VS Code configuration."""

    auto_refresh_interval: int = 10  # minutes
    refresh_cooldown: int = 60  # seconds per-account
    refresh_all_cooldown: int = 120  # seconds global
    stale_threshold: int = 30  # minutes


@dataclass
class AccountConfig:
    """Stored account configuration."""

    id: str
    label: str
    token: str


@dataclass
class Config:
    """Full application configuration."""

    settings: Settings = field(default_factory=Settings)
    accounts: List[AccountConfig] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "settings": asdict(self.settings),
            "accounts": [asdict(a) for a in self.accounts],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Config:
        settings = Settings(**data.get("settings", {}))
        accounts = [AccountConfig(**a) for a in data.get("accounts", [])]
        return cls(settings=settings, accounts=accounts)


class ConfigManager:
    """Manages loading and saving configuration to disk."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or _default_config_dir()
        self.config_file = self.config_dir / "config.json"
        self._config: Config | None = None

    def load(self) -> Config:
        """Load configuration from disk, creating defaults if needed."""
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = Config.from_dict(data)
            except (json.JSONDecodeError, KeyError, TypeError):
                self._config = Config()
        else:
            self._config = Config()

        return self._config

    def save(self, config: Config | None = None) -> None:
        """Save configuration to disk."""
        if config is not None:
            self._config = config

        if self._config is None:
            return

        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._config.to_dict(), f, indent=2)

    def add_account(self, account_id: str, label: str, token: str) -> None:
        """Add or update an account in the configuration."""
        config = self.load()
        for existing in config.accounts:
            if existing.id == account_id:
                existing.label = label
                existing.token = token
                self.save()
                return
        config.accounts.append(AccountConfig(id=account_id, label=label, token=token))
        self.save()

    def remove_account(self, account_id: str) -> bool:
        """Remove an account from the configuration. Returns True if found."""
        config = self.load()
        original_len = len(config.accounts)
        config.accounts = [a for a in config.accounts if a.id != account_id]
        if len(config.accounts) < original_len:
            self.save()
            return True
        return False

    def update_settings(self, **kwargs: int) -> None:
        """Update specific settings values."""
        config = self.load()
        for key, value in kwargs.items():
            if hasattr(config.settings, key):
                setattr(config.settings, key, value)
        self.save()
