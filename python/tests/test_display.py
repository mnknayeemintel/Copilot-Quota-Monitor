"""Tests for the display module."""

from copilot_monitor.display import (
    _bar_color,
    _format_reset_date,
    _progress_bar,
    _sort_quotas,
    _status_color,
    display_status_line,
    GREEN,
    YELLOW,
    RED,
)
from copilot_monitor.models import ErrorType, QuotaData


class TestBarColor:
    def test_green_low_usage(self) -> None:
        assert _bar_color(30) == GREEN

    def test_yellow_medium_usage(self) -> None:
        assert _bar_color(60) == YELLOW

    def test_red_high_usage(self) -> None:
        assert _bar_color(90) == RED


class TestStatusColor:
    def test_green_high_remaining(self) -> None:
        assert _status_color(60) == GREEN

    def test_yellow_medium_remaining(self) -> None:
        assert _status_color(35) == YELLOW

    def test_red_low_remaining(self) -> None:
        assert _status_color(10) == RED


class TestFormatResetDate:
    def test_valid_date(self) -> None:
        result = _format_reset_date("2025-04-01T00:00:00Z")
        assert "Apr" in result
        assert "2025" in result

    def test_empty_string(self) -> None:
        assert _format_reset_date("") == ""

    def test_invalid_date(self) -> None:
        result = _format_reset_date("not-a-date")
        assert result == "not-a-date"


class TestSortQuotas:
    def test_valid_accounts_sorted_by_remaining(self) -> None:
        q1 = QuotaData(account_id="a", account_label="A", percent_remaining=30)
        q2 = QuotaData(account_id="b", account_label="B", percent_remaining=80)
        q3 = QuotaData(account_id="c", account_label="C", percent_remaining=50)
        sorted_q = _sort_quotas([q1, q2, q3])
        assert sorted_q[0].account_id == "b"
        assert sorted_q[1].account_id == "c"
        assert sorted_q[2].account_id == "a"

    def test_errors_sorted_to_bottom(self) -> None:
        q_ok = QuotaData(account_id="ok", account_label="OK", percent_remaining=50)
        q_err = QuotaData(
            account_id="err", account_label="Err", error="Network error",
            error_type=ErrorType.NETWORK,
        )
        sorted_q = _sort_quotas([q_err, q_ok])
        assert sorted_q[0].account_id == "ok"
        assert sorted_q[1].account_id == "err"

    def test_free_plan_sorted_to_bottom(self) -> None:
        q_ok = QuotaData(account_id="ok", account_label="OK", percent_remaining=50)
        q_free = QuotaData(
            account_id="free", account_label="Free",
            error="Free -- No premium", error_type=ErrorType.FREE_PLAN,
        )
        sorted_q = _sort_quotas([q_free, q_ok])
        assert sorted_q[0].account_id == "ok"
        assert sorted_q[1].account_id == "free"


class TestDisplayStatusLine:
    def test_empty_list(self) -> None:
        result = display_status_line([])
        assert "No accounts" in result

    def test_all_errors(self) -> None:
        q = QuotaData(
            account_id="x", account_label="X",
            error="fail", error_type=ErrorType.NETWORK,
        )
        result = display_status_line([q])
        assert "Error" in result

    def test_best_account_selected(self) -> None:
        q1 = QuotaData(
            account_id="a", account_label="Alice", percent_remaining=30,
        )
        q2 = QuotaData(
            account_id="b", account_label="Bob", percent_remaining=80,
        )
        result = display_status_line([q1, q2])
        assert "80" in result  # 80% or 80.0%
        assert "Bob" in result
        assert "2 account(s)" in result
