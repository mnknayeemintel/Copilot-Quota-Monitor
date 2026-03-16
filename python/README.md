# Copilot Quota Monitor — Python CLI

A command-line tool for monitoring GitHub Copilot premium quota usage across multiple GitHub accounts. This is the Python equivalent of the [VS Code extension](../README.md).

## Features

- **Multi-account support** — Monitor quota for multiple GitHub accounts simultaneously
- **Color-coded terminal output** — Green/yellow/red progress bars based on usage
- **Rate limiting** — Per-account and global cooldowns to protect API quota
- **Data caching** — Persists quota data between runs
- **Configurable settings** — Auto-refresh interval, cooldowns, stale threshold

## Installation

### From source

```bash
cd python
pip install -e .
```

### Using requirements

```bash
cd python
pip install -r requirements.txt
```

## Quick Start

### 1. Add a GitHub account

You'll need a GitHub personal access token with the `copilot` scope.

```bash
# Interactive (prompts for token securely)
python -m copilot_monitor add --label "myusername"

# Non-interactive
python -m copilot_monitor add --label "myusername" --token "ghp_xxxxxxxxxxxx"
```

### 2. Check your quota

```bash
python -m copilot_monitor check
```

Example output:

```
══════════════════════════════════════════════════════════
  Copilot Quota Monitor
  Last refresh: 02:30 PM
══════════════════════════════════════════════════════════

  myusername  (Copilot Pro)
  [████████████████████████░░░░░░] 72.5% remaining
  83 / 300 requests used
  Reset: Apr 01, 2025 │ Updated: 02:30 PM
```

### 3. Quick status check

```bash
python -m copilot_monitor status
```

Output: `72.5% remaining — myusername (best of 1 account(s))`

## Commands

| Command | Description |
|---------|-------------|
| `check` | Fetch and display quota for all configured accounts |
| `status` | Show a one-line status summary (uses cache if available) |
| `add` | Add a GitHub account (with token) |
| `remove <id>` | Remove a configured account |
| `list` | List all configured accounts |
| `config` | Show or update settings |
| `cache-clear` | Clear all cached data |

### Options

| Flag | Description |
|------|-------------|
| `--version` | Show version |
| `-v, --verbose` | Enable verbose/debug logging |

## Configuration

Settings are stored in `~/.config/copilot-quota-monitor/config.json`.

```bash
# View current settings
python -m copilot_monitor config

# Update settings
python -m copilot_monitor config --auto-refresh-interval 15
python -m copilot_monitor config --refresh-cooldown 90
python -m copilot_monitor config --stale-threshold 60
```

| Setting | Default | Description |
|---------|---------|-------------|
| `auto_refresh_interval` | 10 | Auto-refresh interval in minutes (min: 5) |
| `refresh_cooldown` | 60 | Per-account cooldown in seconds (min: 30) |
| `refresh_all_cooldown` | 120 | Global refresh cooldown in seconds (min: 60) |
| `stale_threshold` | 30 | Minutes before data is considered stale (min: 5) |

## Architecture

The Python version mirrors the TypeScript VS Code extension architecture:

| Python Module | TypeScript Equivalent | Purpose |
|--------------|----------------------|---------|
| `models.py` | `types.ts` | Data models and types |
| `quota_service.py` | `quotaService.ts` | GitHub API interaction |
| `rate_limiter.py` | `rateLimiter.ts` | Rate limiting and request throttling |
| `cache.py` | `cache.ts` | Data persistence (JSON file) |
| `config.py` | VS Code settings | Configuration management |
| `display.py` | `webview/` | Terminal UI output |
| `__main__.py` | `extension.ts` | CLI entry point |

### API

The tool uses the same GitHub API endpoint as the VS Code extension:

```
GET https://api.github.com/copilot_internal/user
Authorization: Bearer {token}
X-GitHub-Api-Version: 2025-05-01
```

## Development

### Setup

```bash
cd python
pip install -r requirements-dev.txt
```

### Run tests

```bash
python -m pytest tests/ -v
```

### Project structure

```
python/
├── copilot_monitor/
│   ├── __init__.py          # Package metadata
│   ├── __main__.py          # CLI entry point
│   ├── models.py            # Data models
│   ├── quota_service.py     # GitHub API interaction
│   ├── rate_limiter.py      # Rate limiting
│   ├── cache.py             # JSON file-based caching
│   ├── config.py            # Configuration management
│   └── display.py           # Terminal display
├── tests/
│   ├── test_models.py
│   ├── test_quota_service.py
│   ├── test_rate_limiter.py
│   ├── test_cache.py
│   ├── test_config.py
│   └── test_display.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Requirements

- Python 3.9+
- `aiohttp` — Async HTTP client for GitHub API calls

## License

Same license as the main project.
