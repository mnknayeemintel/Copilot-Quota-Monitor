"""Data models for Copilot Quota Monitor, equivalent to types.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ErrorType(Enum):
    AUTH = "auth"
    NETWORK = "network"
    RATE_LIMIT = "rateLimit"
    NO_PLAN = "noPlan"
    FREE_PLAN = "freePlan"
    API_CHANGED = "apiChanged"
    UNKNOWN = "unknown"


@dataclass
class QuotaData:
    """Quota information for a single GitHub account."""

    account_id: str
    account_label: str
    plan: str = ""
    entitlement: int = 0
    percent_remaining: float = 0.0
    percent_used: float = 0.0
    used: int = 0
    overage_permitted: bool = False
    overage_count: int = 0
    reset_date: str = ""
    fetched_at: float = 0.0
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON storage."""
        return {
            "account_id": self.account_id,
            "account_label": self.account_label,
            "plan": self.plan,
            "entitlement": self.entitlement,
            "percent_remaining": self.percent_remaining,
            "percent_used": self.percent_used,
            "used": self.used,
            "overage_permitted": self.overage_permitted,
            "overage_count": self.overage_count,
            "reset_date": self.reset_date,
            "fetched_at": self.fetched_at,
            "error": self.error,
            "error_type": self.error_type.value if self.error_type else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> QuotaData:
        """Deserialize from dictionary."""
        error_type = None
        if data.get("error_type"):
            try:
                error_type = ErrorType(data["error_type"])
            except ValueError:
                error_type = ErrorType.UNKNOWN
        return cls(
            account_id=data["account_id"],
            account_label=data["account_label"],
            plan=data.get("plan", ""),
            entitlement=data.get("entitlement", 0),
            percent_remaining=data.get("percent_remaining", 0.0),
            percent_used=data.get("percent_used", 0.0),
            used=data.get("used", 0),
            overage_permitted=data.get("overage_permitted", False),
            overage_count=data.get("overage_count", 0),
            reset_date=data.get("reset_date", ""),
            fetched_at=data.get("fetched_at", 0.0),
            error=data.get("error"),
            error_type=error_type,
        )


@dataclass
class Account:
    """A GitHub account with an access token."""

    id: str
    label: str
    token: str


@dataclass
class CopilotUserInfoResponse:
    """Parsed response from the GitHub Copilot API."""

    copilot_plan: Optional[str] = None
    entitlement: int = 0
    percent_remaining: float = 0.0
    overage_permitted: bool = False
    overage_count: int = 0
    quota_reset_date: str = ""
    has_premium_interactions: bool = False
