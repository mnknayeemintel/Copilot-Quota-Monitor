"""Terminal display for quota information, equivalent to the webview UI."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from typing import List

from .models import ErrorType, QuotaData
from .quota_service import get_plan_display_name

# ANSI color codes
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_RED = "\033[41m"


def _bar_color(percent_used: float) -> str:
    """Return an ANSI color code based on usage percentage."""
    if percent_used < 50:
        return GREEN
    elif percent_used < 80:
        return YELLOW
    else:
        return RED


def _status_color(percent_remaining: float) -> str:
    """Return an ANSI color code based on remaining percentage."""
    if percent_remaining > 50:
        return GREEN
    elif percent_remaining >= 20:
        return YELLOW
    else:
        return RED


def _progress_bar(percent_used: float, width: int = 30) -> str:
    """Render a colored progress bar string."""
    clamped = max(0.0, min(100.0, percent_used))
    filled = int(width * clamped / 100)
    empty = width - filled
    color = _bar_color(percent_used)
    bar = f"{color}{'█' * filled}{DIM}{'░' * empty}{RESET}"
    return f"[{bar}]"


def _format_reset_date(reset_date: str) -> str:
    """Format an ISO reset date to a human-readable string."""
    if not reset_date:
        return ""
    try:
        dt = datetime.fromisoformat(reset_date.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return reset_date


def _format_fetched_at(fetched_at: float) -> str:
    """Format a Unix timestamp to a human-readable time string."""
    if not fetched_at:
        return ""
    try:
        dt = datetime.fromtimestamp(fetched_at)
        return dt.strftime("%I:%M %p")
    except (ValueError, OSError):
        return ""


def _sort_quotas(quotas: List[QuotaData]) -> List[QuotaData]:
    """Sort quotas: valid accounts first (by percent_remaining desc), errors/free last."""

    def sort_key(q: QuotaData) -> tuple:
        is_bottom = q.error_type == ErrorType.FREE_PLAN or q.error is not None
        return (is_bottom, -q.percent_remaining)

    return sorted(quotas, key=sort_key)


def display_quotas(quotas: List[QuotaData], last_refresh: float = 0.0) -> None:
    """Display all quota information in the terminal."""
    term_width = shutil.get_terminal_size((80, 24)).columns

    # Header
    print()
    print(f"{BOLD}{'═' * min(60, term_width)}{RESET}")
    print(f"{BOLD}  Copilot Quota Monitor{RESET}")
    if last_refresh:
        refresh_str = _format_fetched_at(last_refresh)
        print(f"{DIM}  Last refresh: {refresh_str}{RESET}")
    print(f"{BOLD}{'═' * min(60, term_width)}{RESET}")
    print()

    if not quotas:
        print(f"  {DIM}No accounts configured. Use 'add' to add a GitHub token.{RESET}")
        print()
        return

    sorted_quotas = _sort_quotas(quotas)

    for quota in sorted_quotas:
        _display_single_quota(quota)


def _display_single_quota(quota: QuotaData) -> None:
    """Display a single account's quota information."""
    # Error cards
    if quota.error and quota.error_type != ErrorType.FREE_PLAN:
        _display_error_card(quota)
        return

    # Free plan cards
    if quota.error_type == ErrorType.FREE_PLAN:
        _display_free_card(quota)
        return

    # Normal quota card
    plan_name = get_plan_display_name(quota.plan)
    color = _status_color(quota.percent_remaining)
    pct_display = round(max(0, quota.percent_remaining), 1)

    print(f"  {BOLD}{quota.account_label}{RESET}  {DIM}({plan_name}){RESET}")
    print(f"  {_progress_bar(quota.percent_used)} {color}{pct_display}% remaining{RESET}")
    print(f"  {DIM}{quota.used} / {quota.entitlement} requests used{RESET}", end="")

    if quota.overage_count > 0:
        print(f"  {RED}{BOLD}+{quota.overage_count} overage{RESET}", end="")

    print()

    details = []
    if quota.reset_date:
        details.append(f"Reset: {_format_reset_date(quota.reset_date)}")
    if quota.fetched_at:
        details.append(f"Updated: {_format_fetched_at(quota.fetched_at)}")
    if details:
        print(f"  {DIM}{' │ '.join(details)}{RESET}")

    print()


def _display_error_card(quota: QuotaData) -> None:
    """Display an error account card."""
    print(f"  {RED}{BOLD}{quota.account_label}{RESET}")
    print(f"  {RED}✗ {quota.error}{RESET}")
    if quota.fetched_at:
        print(f"  {DIM}Updated: {_format_fetched_at(quota.fetched_at)}{RESET}")
    print()


def _display_free_card(quota: QuotaData) -> None:
    """Display a free-plan account card."""
    plan_name = get_plan_display_name(quota.plan)
    print(f"  {DIM}{quota.account_label}  ({plan_name}){RESET}")
    print(f"  {DIM}Free plan — no premium quota{RESET}")
    if quota.fetched_at:
        print(f"  {DIM}Updated: {_format_fetched_at(quota.fetched_at)}{RESET}")
    print()


def display_status_line(quotas: List[QuotaData]) -> str:
    """Return a single status line (like the VS Code status bar)."""
    valid = [q for q in quotas if not q.error]
    if not valid:
        if not quotas:
            return f"{DIM}No accounts configured{RESET}"
        return f"{RED}Error fetching quota{RESET}"

    best = max(valid, key=lambda q: q.percent_remaining)
    pct = round(max(0, best.percent_remaining), 1)
    color = _status_color(best.percent_remaining)
    return (
        f"{color}{BOLD}{pct}%{RESET} remaining — "
        f"{best.account_label} (best of {len(valid)} account(s))"
    )
