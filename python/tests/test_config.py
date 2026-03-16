"""Tests for the configuration manager."""

from pathlib import Path

from copilot_monitor.config import AccountConfig, Config, ConfigManager, Settings


class TestConfigManager:
    def test_default_config(self, tmp_path: Path) -> None:
        cm = ConfigManager(config_dir=tmp_path)
        config = cm.load()
        assert config.settings.auto_refresh_interval == 10
        assert config.settings.refresh_cooldown == 60
        assert config.accounts == []

    def test_save_and_load(self, tmp_path: Path) -> None:
        cm = ConfigManager(config_dir=tmp_path)
        config = cm.load()
        config.settings.auto_refresh_interval = 15
        cm.save()

        cm2 = ConfigManager(config_dir=tmp_path)
        config2 = cm2.load()
        assert config2.settings.auto_refresh_interval == 15

    def test_add_account(self, tmp_path: Path) -> None:
        cm = ConfigManager(config_dir=tmp_path)
        cm.add_account("id1", "User1", "token123")
        config = cm.load()
        assert len(config.accounts) == 1
        assert config.accounts[0].id == "id1"
        assert config.accounts[0].label == "User1"
        assert config.accounts[0].token == "token123"

    def test_add_account_updates_existing(self, tmp_path: Path) -> None:
        cm = ConfigManager(config_dir=tmp_path)
        cm.add_account("id1", "User1", "token_old")
        cm.add_account("id1", "User1 Updated", "token_new")
        config = cm.load()
        assert len(config.accounts) == 1
        assert config.accounts[0].label == "User1 Updated"
        assert config.accounts[0].token == "token_new"

    def test_remove_account(self, tmp_path: Path) -> None:
        cm = ConfigManager(config_dir=tmp_path)
        cm.add_account("id1", "User1", "t1")
        cm.add_account("id2", "User2", "t2")
        assert cm.remove_account("id1") is True
        config = cm.load()
        assert len(config.accounts) == 1
        assert config.accounts[0].id == "id2"

    def test_remove_nonexistent_account(self, tmp_path: Path) -> None:
        cm = ConfigManager(config_dir=tmp_path)
        assert cm.remove_account("nonexistent") is False

    def test_update_settings(self, tmp_path: Path) -> None:
        cm = ConfigManager(config_dir=tmp_path)
        cm.update_settings(auto_refresh_interval=20, stale_threshold=60)
        config = cm.load()
        assert config.settings.auto_refresh_interval == 20
        assert config.settings.stale_threshold == 60
        # Unchanged settings should keep defaults
        assert config.settings.refresh_cooldown == 60

    def test_config_round_trip(self) -> None:
        config = Config(
            settings=Settings(auto_refresh_interval=15),
            accounts=[AccountConfig(id="a", label="A", token="t")],
        )
        d = config.to_dict()
        restored = Config.from_dict(d)
        assert restored.settings.auto_refresh_interval == 15
        assert len(restored.accounts) == 1
        assert restored.accounts[0].id == "a"
