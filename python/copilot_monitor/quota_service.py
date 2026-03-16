"""GitHub Copilot API interaction, equivalent to quotaService.ts."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List

import aiohttp

from .models import Account, CopilotUserInfoResponse, ErrorType, QuotaData
from .rate_limiter import RateLimiter

API_URL = "https://api.github.com/copilot_internal/user"
API_VERSION = "2025-05-01"

logger = logging.getLogger("copilot_monitor")

PLAN_DISPLAY_NAMES = {
    "individual": "Copilot Pro",
    "individual_pro": "Copilot Pro+",
    "business": "Copilot Business",
    "enterprise": "Copilot Enterprise",
}


def get_plan_display_name(plan: str | None) -> str:
    """Map API plan identifiers to human-readable display names."""
    if plan is None:
        return "Copilot Free"
    return PLAN_DISPLAY_NAMES.get(plan, "Copilot Free")


class QuotaService:
    """Fetches Copilot quota data from the GitHub API."""

    def __init__(self, rate_limiter: RateLimiter) -> None:
        self._rate_limiter = rate_limiter

    async def fetch_quota(self, account: Account) -> QuotaData:
        """Fetch quota data for a single account."""
        logger.info("Fetching quota for %s...", account.label)

        await self._rate_limiter.acquire_slot()
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {account.token}",
                    "X-GitHub-Api-Version": API_VERSION,
                    "Accept": "application/json",
                }
                async with session.get(API_URL, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(
                            "HTTP %d for %s", response.status, account.label
                        )
                        return self._build_error_quota(account, response.status)

                    json_data = await response.json()
                    logger.info(
                        "Success for %s: plan=%s",
                        account.label,
                        json_data.get("copilot_plan"),
                    )
                    return self._parse_response(account, json_data)

        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.error("Network error for %s: %s", account.label, exc)
            return QuotaData(
                account_id=account.id,
                account_label=account.label,
                fetched_at=time.time(),
                error="Network error",
                error_type=ErrorType.NETWORK,
            )
        finally:
            self._rate_limiter.release_slot()

    async def fetch_all_quotas(self, accounts: List[Account]) -> List[QuotaData]:
        """Fetch quota data for multiple accounts concurrently."""
        tasks = [self.fetch_quota(account) for account in accounts]
        return await asyncio.gather(*tasks)

    def _parse_response(self, account: Account, json_data: dict) -> QuotaData:
        """Parse a GitHub API response into a QuotaData object."""
        copilot_plan = json_data.get("copilot_plan")
        plan_name = get_plan_display_name(copilot_plan)

        quota_snapshots = json_data.get("quota_snapshots") or {}
        premium = quota_snapshots.get("premium_interactions")

        if not premium:
            if not copilot_plan:
                return QuotaData(
                    account_id=account.id,
                    account_label=account.label,
                    fetched_at=time.time(),
                    error="No Copilot plan",
                    error_type=ErrorType.NO_PLAN,
                )
            return QuotaData(
                account_id=account.id,
                account_label=account.label,
                plan=copilot_plan or "",
                reset_date=json_data.get("quota_reset_date", ""),
                fetched_at=time.time(),
                error=f"{plan_name} -- No premium quota",
                error_type=ErrorType.FREE_PLAN,
            )

        entitlement = premium.get("entitlement", 0)
        percent_remaining = premium.get("percent_remaining", 0.0)
        used = max(0, entitlement * (1 - percent_remaining / 100))
        percent_used = 100 - percent_remaining

        return QuotaData(
            account_id=account.id,
            account_label=account.label,
            plan=copilot_plan or "",
            entitlement=entitlement,
            percent_remaining=percent_remaining,
            percent_used=round(percent_used, 1),
            used=round(used),
            overage_permitted=premium.get("overage_permitted", False),
            overage_count=premium.get("overage_count", 0),
            reset_date=json_data.get("quota_reset_date", ""),
            fetched_at=time.time(),
        )

    @staticmethod
    def _build_error_quota(account: Account, status: int) -> QuotaData:
        """Create an error QuotaData from an HTTP status code."""
        if status in (401, 403):
            error = "Authentication failed"
            error_type = ErrorType.AUTH
        elif status == 429:
            error = "Rate limited"
            error_type = ErrorType.RATE_LIMIT
        elif status == 404:
            error = "API endpoint not found"
            error_type = ErrorType.API_CHANGED
        else:
            error = f"HTTP {status}"
            error_type = ErrorType.UNKNOWN

        return QuotaData(
            account_id=account.id,
            account_label=account.label,
            fetched_at=time.time(),
            error=error,
            error_type=error_type,
        )
