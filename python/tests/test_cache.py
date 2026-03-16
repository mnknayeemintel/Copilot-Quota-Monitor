"""Tests for the cache module."""

import json
import tempfile
from pathlib import Path

from copilot_monitor.cache import Cache
from copilot_monitor.models import ErrorType, QuotaData


class TestCache:
    def _make_cache(self, tmp_path: Path) -> Cache:
        return Cache(tmp_path)

    def test_save_and_load_quota(self, tmp_path: Path) -> None:
        cache = self._make_cache(tmp_path)
        quota = QuotaData(
            account_id="user1",
            account_label="User One",
            plan="individual",
            entitlement=300,
            percent_remaining=72.5,
            percent_used=27.5,
            used=83,
            fetched_at=1710000000.0,
        )
        cache.save_quota("user1", quota)
        loaded = cache.load_quota("user1")
        assert loaded is not None
        assert loaded.account_id == "user1"
        assert loaded.percent_remaining == 72.5

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        cache = self._make_cache(tmp_path)
        assert cache.load_quota("nonexistent") is None

    def test_load_all_quotas(self, tmp_path: Path) -> None:
        cache = self._make_cache(tmp_path)
        q1 = QuotaData(account_id="a1", account_label="A1", fetched_at=1.0)
        q2 = QuotaData(account_id="a2", account_label="A2", fetched_at=2.0)
        cache.save_quota("a1", q1)
        cache.save_quota("a2", q2)
        all_q = cache.load_all_quotas()
        assert len(all_q) == 2
        assert "a1" in all_q
        assert "a2" in all_q

    def test_remove_account(self, tmp_path: Path) -> None:
        cache = self._make_cache(tmp_path)
        q = QuotaData(account_id="del", account_label="Del", fetched_at=1.0)
        cache.save_quota("del", q)
        assert cache.load_quota("del") is not None
        cache.remove_account("del")
        assert cache.load_quota("del") is None

    def test_clear_all(self, tmp_path: Path) -> None:
        cache = self._make_cache(tmp_path)
        cache.save_quota("x", QuotaData(account_id="x", account_label="X", fetched_at=1.0))
        cache.save_last_refresh(100.0)
        cache.clear_all()
        assert cache.load_all_quotas() == {}
        assert cache.load_last_refresh() == 0.0

    def test_last_refresh(self, tmp_path: Path) -> None:
        cache = self._make_cache(tmp_path)
        assert cache.load_last_refresh() == 0.0
        cache.save_last_refresh(12345.0)
        assert cache.load_last_refresh() == 12345.0

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        """Data should persist when creating a new Cache pointing to same dir."""
        cache1 = self._make_cache(tmp_path)
        cache1.save_quota("p", QuotaData(account_id="p", account_label="P", fetched_at=1.0))
        cache1.save_last_refresh(999.0)

        cache2 = self._make_cache(tmp_path)
        loaded = cache2.load_quota("p")
        assert loaded is not None
        assert loaded.account_id == "p"
        assert cache2.load_last_refresh() == 999.0
