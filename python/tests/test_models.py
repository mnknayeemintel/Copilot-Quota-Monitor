"""Tests for the data models."""

from copilot_monitor.models import ErrorType, QuotaData


class TestQuotaData:
    def test_round_trip_serialization(self) -> None:
        """QuotaData should survive to_dict/from_dict round-trip."""
        original = QuotaData(
            account_id="user1",
            account_label="User One",
            plan="individual",
            entitlement=300,
            percent_remaining=72.5,
            percent_used=27.5,
            used=83,
            overage_permitted=True,
            overage_count=0,
            reset_date="2025-04-01T00:00:00Z",
            fetched_at=1710000000.0,
        )
        d = original.to_dict()
        restored = QuotaData.from_dict(d)
        assert restored.account_id == original.account_id
        assert restored.account_label == original.account_label
        assert restored.plan == original.plan
        assert restored.entitlement == original.entitlement
        assert restored.percent_remaining == original.percent_remaining
        assert restored.percent_used == original.percent_used
        assert restored.used == original.used
        assert restored.overage_permitted == original.overage_permitted
        assert restored.reset_date == original.reset_date
        assert restored.error is None
        assert restored.error_type is None

    def test_round_trip_with_error(self) -> None:
        """Error fields should survive round-trip."""
        original = QuotaData(
            account_id="user2",
            account_label="User Two",
            fetched_at=1710000000.0,
            error="Authentication failed",
            error_type=ErrorType.AUTH,
        )
        d = original.to_dict()
        restored = QuotaData.from_dict(d)
        assert restored.error == "Authentication failed"
        assert restored.error_type == ErrorType.AUTH

    def test_from_dict_unknown_error_type(self) -> None:
        """Unknown error_type values should map to UNKNOWN."""
        data = {
            "account_id": "u",
            "account_label": "U",
            "error_type": "somethingNew",
        }
        q = QuotaData.from_dict(data)
        assert q.error_type == ErrorType.UNKNOWN

    def test_from_dict_defaults(self) -> None:
        """Missing optional fields should use defaults."""
        data = {"account_id": "x", "account_label": "X"}
        q = QuotaData.from_dict(data)
        assert q.plan == ""
        assert q.entitlement == 0
        assert q.percent_remaining == 0.0
        assert q.error is None
        assert q.error_type is None
