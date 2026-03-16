"""Rate limiting for API requests, equivalent to rateLimiter.ts."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class CooldownCheck:
    """Result of a cooldown check."""

    allowed: bool
    wait_seconds: int


class RateLimiter:
    """Controls request rate and concurrency, equivalent to the TypeScript RateLimiter."""

    def __init__(
        self,
        per_account_cooldown: int = 60,
        refresh_all_cooldown: int = 120,
        max_concurrent: int = 3,
    ) -> None:
        self._per_account_cooldown = per_account_cooldown
        self._refresh_all_cooldown = refresh_all_cooldown
        self._max_concurrent = max_concurrent
        self._per_account_last_refresh: dict[str, float] = {}
        self._last_refresh_all: float = 0.0
        self._semaphore = asyncio.Semaphore(max_concurrent)

    @property
    def per_account_cooldown(self) -> int:
        return self._per_account_cooldown

    @per_account_cooldown.setter
    def per_account_cooldown(self, value: int) -> None:
        self._per_account_cooldown = value

    @property
    def refresh_all_cooldown(self) -> int:
        return self._refresh_all_cooldown

    @refresh_all_cooldown.setter
    def refresh_all_cooldown(self, value: int) -> None:
        self._refresh_all_cooldown = value

    def can_refresh(self, account_id: str) -> CooldownCheck:
        """Check if a specific account can be refreshed."""
        cooldown = self._per_account_cooldown
        last_refresh = self._per_account_last_refresh.get(account_id, 0.0)
        elapsed = time.time() - last_refresh
        if elapsed >= cooldown:
            return CooldownCheck(allowed=True, wait_seconds=0)
        remaining = int(cooldown - elapsed) + 1
        return CooldownCheck(allowed=False, wait_seconds=remaining)

    def can_refresh_all(self) -> CooldownCheck:
        """Check if a global refresh-all is allowed."""
        cooldown = self._refresh_all_cooldown
        elapsed = time.time() - self._last_refresh_all
        if elapsed >= cooldown:
            return CooldownCheck(allowed=True, wait_seconds=0)
        remaining = int(cooldown - elapsed) + 1
        return CooldownCheck(allowed=False, wait_seconds=remaining)

    def record_refresh(self, account_id: str) -> None:
        """Record that an account was just refreshed."""
        self._per_account_last_refresh[account_id] = time.time()

    def record_refresh_all(self) -> None:
        """Record that a global refresh-all just happened."""
        self._last_refresh_all = time.time()

    def reset_cooldown(self, account_id: str) -> None:
        """Clear the cooldown for a specific account."""
        self._per_account_last_refresh.pop(account_id, None)

    def reset_all_cooldowns(self) -> None:
        """Clear all cooldowns."""
        self._per_account_last_refresh.clear()
        self._last_refresh_all = 0.0

    async def acquire_slot(self) -> None:
        """Acquire a concurrent request slot (max 3 concurrent)."""
        await self._semaphore.acquire()

    def release_slot(self) -> None:
        """Release a concurrent request slot."""
        self._semaphore.release()
