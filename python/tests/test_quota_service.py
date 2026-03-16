"""Tests for the quota service."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from copilot_monitor.models import Account, ErrorType
from copilot_monitor.quota_service import QuotaService, get_plan_display_name
from copilot_monitor.rate_limiter import RateLimiter


class TestGetPlanDisplayName:
    def test_individual(self) -> None:
        assert get_plan_display_name("individual") == "Copilot Pro"

    def test_individual_pro(self) -> None:
        assert get_plan_display_name("individual_pro") == "Copilot Pro+"

    def test_business(self) -> None:
        assert get_plan_display_name("business") == "Copilot Business"

    def test_enterprise(self) -> None:
        assert get_plan_display_name("enterprise") == "Copilot Enterprise"

    def test_none(self) -> None:
        assert get_plan_display_name(None) == "Copilot Free"

    def test_unknown(self) -> None:
        assert get_plan_display_name("something_else") == "Copilot Free"


class TestQuotaServiceParseResponse:
    def _make_service(self) -> QuotaService:
        rl = RateLimiter()
        return QuotaService(rl)

    def _make_account(self) -> Account:
        return Account(id="user1", label="User One", token="fake-token")

    def test_parse_normal_response(self) -> None:
        svc = self._make_service()
        account = self._make_account()
        json_data = {
            "copilot_plan": "individual",
            "quota_snapshots": {
                "premium_interactions": {
                    "entitlement": 300,
                    "percent_remaining": 72.5,
                    "overage_permitted": True,
                    "overage_count": 0,
                }
            },
            "quota_reset_date": "2025-04-01T00:00:00Z",
        }
        result = svc._parse_response(account, json_data)
        assert result.account_id == "user1"
        assert result.plan == "individual"
        assert result.entitlement == 300
        assert result.percent_remaining == 72.5
        assert result.percent_used == 27.5
        assert result.used == 82  # round(300 * 0.275) = round(82.5) = 82 (banker's rounding)
        assert result.overage_permitted is True
        assert result.error is None

    def test_parse_no_plan(self) -> None:
        svc = self._make_service()
        account = self._make_account()
        json_data = {}
        result = svc._parse_response(account, json_data)
        assert result.error == "No Copilot plan"
        assert result.error_type == ErrorType.NO_PLAN

    def test_parse_free_plan(self) -> None:
        svc = self._make_service()
        account = self._make_account()
        json_data = {"copilot_plan": "individual"}
        result = svc._parse_response(account, json_data)
        assert result.error_type == ErrorType.FREE_PLAN
        assert "No premium quota" in (result.error or "")

    def test_parse_with_overage(self) -> None:
        svc = self._make_service()
        account = self._make_account()
        json_data = {
            "copilot_plan": "individual",
            "quota_snapshots": {
                "premium_interactions": {
                    "entitlement": 100,
                    "percent_remaining": -10.0,
                    "overage_permitted": True,
                    "overage_count": 10,
                }
            },
            "quota_reset_date": "2025-04-01T00:00:00Z",
        }
        result = svc._parse_response(account, json_data)
        assert result.percent_used == 110.0
        assert result.overage_count == 10
        assert result.error is None

    def test_build_error_quota_auth(self) -> None:
        account = self._make_account()
        result = QuotaService._build_error_quota(account, 401)
        assert result.error == "Authentication failed"
        assert result.error_type == ErrorType.AUTH

    def test_build_error_quota_rate_limit(self) -> None:
        account = self._make_account()
        result = QuotaService._build_error_quota(account, 429)
        assert result.error == "Rate limited"
        assert result.error_type == ErrorType.RATE_LIMIT

    def test_build_error_quota_not_found(self) -> None:
        account = self._make_account()
        result = QuotaService._build_error_quota(account, 404)
        assert result.error == "API endpoint not found"
        assert result.error_type == ErrorType.API_CHANGED

    def test_build_error_quota_unknown(self) -> None:
        account = self._make_account()
        result = QuotaService._build_error_quota(account, 500)
        assert result.error == "HTTP 500"
        assert result.error_type == ErrorType.UNKNOWN

    def test_build_error_quota_forbidden(self) -> None:
        account = self._make_account()
        result = QuotaService._build_error_quota(account, 403)
        assert result.error == "Authentication failed"
        assert result.error_type == ErrorType.AUTH
