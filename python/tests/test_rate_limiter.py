"""Tests for the rate limiter."""

import asyncio
import time
from unittest.mock import patch

from copilot_monitor.rate_limiter import RateLimiter


class TestRateLimiter:
    def test_can_refresh_initially_allowed(self) -> None:
        """First refresh for an account should always be allowed."""
        rl = RateLimiter(per_account_cooldown=60)
        check = rl.can_refresh("account1")
        assert check.allowed is True
        assert check.wait_seconds == 0

    def test_can_refresh_blocked_after_record(self) -> None:
        """After recording a refresh, the account should be on cooldown."""
        rl = RateLimiter(per_account_cooldown=60)
        rl.record_refresh("account1")
        check = rl.can_refresh("account1")
        assert check.allowed is False
        assert check.wait_seconds > 0

    def test_can_refresh_allowed_after_cooldown(self) -> None:
        """After cooldown expires, the account should be allowed again."""
        rl = RateLimiter(per_account_cooldown=1)
        rl.record_refresh("account1")
        # Simulate time passing
        rl._per_account_last_refresh["account1"] = time.time() - 2
        check = rl.can_refresh("account1")
        assert check.allowed is True

    def test_can_refresh_all_initially_allowed(self) -> None:
        rl = RateLimiter(refresh_all_cooldown=120)
        check = rl.can_refresh_all()
        assert check.allowed is True

    def test_can_refresh_all_blocked_after_record(self) -> None:
        rl = RateLimiter(refresh_all_cooldown=120)
        rl.record_refresh_all()
        check = rl.can_refresh_all()
        assert check.allowed is False
        assert check.wait_seconds > 0

    def test_reset_cooldown(self) -> None:
        rl = RateLimiter(per_account_cooldown=60)
        rl.record_refresh("account1")
        assert rl.can_refresh("account1").allowed is False
        rl.reset_cooldown("account1")
        assert rl.can_refresh("account1").allowed is True

    def test_reset_all_cooldowns(self) -> None:
        rl = RateLimiter(per_account_cooldown=60, refresh_all_cooldown=120)
        rl.record_refresh("a1")
        rl.record_refresh("a2")
        rl.record_refresh_all()
        rl.reset_all_cooldowns()
        assert rl.can_refresh("a1").allowed is True
        assert rl.can_refresh("a2").allowed is True
        assert rl.can_refresh_all().allowed is True

    def test_semaphore_limits_concurrency(self) -> None:
        """Semaphore should limit concurrent requests to max_concurrent."""
        rl = RateLimiter(max_concurrent=2)

        async def _test() -> None:
            await rl.acquire_slot()
            await rl.acquire_slot()
            # Third acquire should block — use wait_for to verify
            try:
                await asyncio.wait_for(rl.acquire_slot(), timeout=0.1)
                blocked = False
            except asyncio.TimeoutError:
                blocked = True
            assert blocked is True

            # Release one slot and try again
            rl.release_slot()
            await asyncio.wait_for(rl.acquire_slot(), timeout=0.1)
            # Clean up
            rl.release_slot()
            rl.release_slot()

        asyncio.run(_test())

    def test_different_accounts_independent(self) -> None:
        """Cooldown for one account should not affect another."""
        rl = RateLimiter(per_account_cooldown=60)
        rl.record_refresh("a1")
        assert rl.can_refresh("a1").allowed is False
        assert rl.can_refresh("a2").allowed is True
