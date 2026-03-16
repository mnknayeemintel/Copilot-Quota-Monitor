"""JSON-file-based caching, equivalent to cache.ts."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from .models import QuotaData


class Cache:
    """Persists quota data to a JSON file on disk."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._cache_file = cache_dir / "cache.json"
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        """Load cache from disk."""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _flush(self) -> None:
        """Write cache to disk."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self._cache_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def save_quota(self, account_id: str, data: QuotaData) -> None:
        """Store quota data for an account."""
        quotas = self._data.setdefault("quotas", {})
        quotas[account_id] = data.to_dict()
        self._flush()

    def load_quota(self, account_id: str) -> Optional[QuotaData]:
        """Retrieve cached quota data for an account."""
        quotas = self._data.get("quotas", {})
        raw = quotas.get(account_id)
        if raw:
            return QuotaData.from_dict(raw)
        return None

    def load_all_quotas(self) -> Dict[str, QuotaData]:
        """Get all cached quota data."""
        quotas = self._data.get("quotas", {})
        result: Dict[str, QuotaData] = {}
        for account_id, raw in quotas.items():
            try:
                result[account_id] = QuotaData.from_dict(raw)
            except (KeyError, TypeError):
                continue
        return result

    def save_last_refresh(self, timestamp: float) -> None:
        """Store the timestamp of the last global refresh."""
        self._data["last_refresh"] = timestamp
        self._flush()

    def load_last_refresh(self) -> float:
        """Get the timestamp of the last global refresh."""
        return self._data.get("last_refresh", 0.0)

    def remove_account(self, account_id: str) -> None:
        """Remove an account from the cache."""
        quotas = self._data.get("quotas", {})
        quotas.pop(account_id, None)
        self._flush()

    def clear_all(self) -> None:
        """Wipe all cached data."""
        self._data = {}
        self._flush()
