"""CLI entry point for Copilot Quota Monitor.

Usage:
    python -m copilot_monitor check          # Fetch and display all quotas
    python -m copilot_monitor status         # One-line status summary
    python -m copilot_monitor add            # Add a GitHub account
    python -m copilot_monitor remove <id>    # Remove an account
    python -m copilot_monitor list           # List configured accounts
    python -m copilot_monitor config         # Show/update settings
    python -m copilot_monitor cache-clear    # Clear cached data
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import sys
from typing import List

from . import __version__
from .cache import Cache
from .config import AccountConfig, ConfigManager
from .display import display_quotas, display_status_line
from .models import Account, QuotaData
from .quota_service import QuotaService
from .rate_limiter import RateLimiter


def _get_config_manager() -> ConfigManager:
    return ConfigManager()


def _get_cache(config_manager: ConfigManager) -> Cache:
    return Cache(config_manager.config_dir)


def _get_services(config_manager: ConfigManager) -> tuple:
    config = config_manager.load()
    rate_limiter = RateLimiter(
        per_account_cooldown=config.settings.refresh_cooldown,
        refresh_all_cooldown=config.settings.refresh_all_cooldown,
    )
    quota_service = QuotaService(rate_limiter)
    return config, rate_limiter, quota_service


def _accounts_from_config(config_accounts: List[AccountConfig]) -> List[Account]:
    return [
        Account(id=a.id, label=a.label, token=a.token) for a in config_accounts
    ]


def cmd_check(args: argparse.Namespace) -> None:
    """Fetch and display quota for all configured accounts."""
    cm = _get_config_manager()
    cache = _get_cache(cm)
    config, rate_limiter, quota_service = _get_services(cm)

    accounts = _accounts_from_config(config.accounts)
    if not accounts:
        print("No accounts configured. Use 'add' to add a GitHub token.")
        sys.exit(1)

    quotas = asyncio.run(quota_service.fetch_all_quotas(accounts))

    import time

    now = time.time()
    for q in quotas:
        cache.save_quota(q.account_id, q)
    cache.save_last_refresh(now)

    display_quotas(quotas, last_refresh=now)


def cmd_status(args: argparse.Namespace) -> None:
    """Show a one-line status summary (uses cache if available)."""
    cm = _get_config_manager()
    cache = _get_cache(cm)

    cached = cache.load_all_quotas()
    if cached:
        quotas = list(cached.values())
    else:
        config, rate_limiter, quota_service = _get_services(cm)
        accounts = _accounts_from_config(config.accounts)
        if not accounts:
            print("No accounts configured. Use 'add' to add a GitHub token.")
            sys.exit(1)
        quotas = asyncio.run(quota_service.fetch_all_quotas(accounts))

    print(display_status_line(quotas))


def cmd_add(args: argparse.Namespace) -> None:
    """Add a GitHub account by providing a personal access token."""
    cm = _get_config_manager()

    label = args.label or input("Account label (e.g. your GitHub username): ").strip()
    if not label:
        print("Error: Account label is required.")
        sys.exit(1)

    if args.token:
        token = args.token
    else:
        token = getpass.getpass("GitHub token (with copilot scope): ").strip()

    if not token:
        print("Error: Token is required.")
        sys.exit(1)

    # Use label as ID (lowercased, no spaces)
    account_id = args.id or label.lower().replace(" ", "-")

    cm.add_account(account_id, label, token)
    print(f"✓ Account '{label}' added (id: {account_id})")


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove a configured account."""
    cm = _get_config_manager()
    cache = _get_cache(cm)

    if cm.remove_account(args.account_id):
        cache.remove_account(args.account_id)
        print(f"✓ Account '{args.account_id}' removed")
    else:
        print(f"Account '{args.account_id}' not found")
        sys.exit(1)


def cmd_list(args: argparse.Namespace) -> None:
    """List all configured accounts."""
    cm = _get_config_manager()
    config = cm.load()

    if not config.accounts:
        print("No accounts configured. Use 'add' to add a GitHub token.")
        return

    print(f"\nConfigured accounts ({len(config.accounts)}):\n")
    for acct in config.accounts:
        masked_token = acct.token[:4] + "..." + acct.token[-4:] if len(acct.token) > 8 else "****"
        print(f"  • {acct.label} (id: {acct.id}, token: {masked_token})")
    print()


def cmd_config(args: argparse.Namespace) -> None:
    """Show or update settings."""
    cm = _get_config_manager()
    config = cm.load()

    updates = {}
    if args.auto_refresh_interval is not None:
        updates["auto_refresh_interval"] = max(5, args.auto_refresh_interval)
    if args.refresh_cooldown is not None:
        updates["refresh_cooldown"] = max(30, args.refresh_cooldown)
    if args.refresh_all_cooldown is not None:
        updates["refresh_all_cooldown"] = max(60, args.refresh_all_cooldown)
    if args.stale_threshold is not None:
        updates["stale_threshold"] = max(5, args.stale_threshold)

    if updates:
        cm.update_settings(**updates)
        print("✓ Settings updated:")
        for key, value in updates.items():
            print(f"  {key}: {value}")
    else:
        print("\nCurrent settings:\n")
        print(f"  auto_refresh_interval: {config.settings.auto_refresh_interval} minutes")
        print(f"  refresh_cooldown:      {config.settings.refresh_cooldown} seconds")
        print(f"  refresh_all_cooldown:  {config.settings.refresh_all_cooldown} seconds")
        print(f"  stale_threshold:       {config.settings.stale_threshold} minutes")
        print(f"\nConfig file: {cm.config_file}")
    print()


def cmd_cache_clear(args: argparse.Namespace) -> None:
    """Clear all cached data."""
    cm = _get_config_manager()
    cache = _get_cache(cm)
    cache.clear_all()
    print("✓ Cache cleared")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="copilot-quota-monitor",
        description="Monitor GitHub Copilot premium quota usage from the command line.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # check
    subparsers.add_parser("check", help="Fetch and display quota for all accounts")

    # status
    subparsers.add_parser("status", help="Show one-line status summary")

    # add
    add_parser = subparsers.add_parser("add", help="Add a GitHub account")
    add_parser.add_argument("--label", help="Account label (e.g. GitHub username)")
    add_parser.add_argument("--token", help="GitHub personal access token")
    add_parser.add_argument("--id", help="Custom account ID")

    # remove
    remove_parser = subparsers.add_parser("remove", help="Remove a configured account")
    remove_parser.add_argument("account_id", help="Account ID to remove")

    # list
    subparsers.add_parser("list", help="List configured accounts")

    # config
    config_parser = subparsers.add_parser("config", help="Show or update settings")
    config_parser.add_argument(
        "--auto-refresh-interval", type=int, dest="auto_refresh_interval",
        help="Auto-refresh interval in minutes (min: 5)"
    )
    config_parser.add_argument(
        "--refresh-cooldown", type=int, dest="refresh_cooldown",
        help="Per-account cooldown in seconds (min: 30)"
    )
    config_parser.add_argument(
        "--refresh-all-cooldown", type=int, dest="refresh_all_cooldown",
        help="Refresh-all cooldown in seconds (min: 60)"
    )
    config_parser.add_argument(
        "--stale-threshold", type=int, dest="stale_threshold",
        help="Stale threshold in minutes (min: 5)"
    )

    # cache-clear
    subparsers.add_parser("cache-clear", help="Clear cached data")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(name)s] %(message)s",
        )
    else:
        logging.basicConfig(level=logging.WARNING)

    commands = {
        "check": cmd_check,
        "status": cmd_status,
        "add": cmd_add,
        "remove": cmd_remove,
        "list": cmd_list,
        "config": cmd_config,
        "cache-clear": cmd_cache_clear,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
