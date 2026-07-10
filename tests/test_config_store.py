import json

import taskLoggerGUI


def test_config_write_is_atomic_and_token_is_removed_from_json(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    stored_tokens = []
    monkeypatch.setattr(taskLoggerGUI, "CONFIG_FILE", str(config_path))
    monkeypatch.setattr(taskLoggerGUI, "save_dashboard_token", stored_tokens.append)

    config = taskLoggerGUI.DEFAULT_CONFIG.copy()
    config["dashboard_api_token"] = "secret-token"
    warning = taskLoggerGUI.save_config(config)

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    assert warning == ""
    assert stored_tokens == ["secret-token"]
    assert persisted["dashboard_api_token"] == ""


def test_plaintext_token_is_migrated_to_secret_store(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config = taskLoggerGUI.DEFAULT_CONFIG.copy()
    config["dashboard_api_token"] = "legacy-token"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    stored_tokens = []
    monkeypatch.setattr(taskLoggerGUI, "CONFIG_FILE", str(config_path))
    monkeypatch.setattr(taskLoggerGUI, "load_dashboard_token", lambda: "")
    monkeypatch.setattr(taskLoggerGUI, "save_dashboard_token", stored_tokens.append)

    loaded = taskLoggerGUI.load_config()

    assert loaded["dashboard_api_token"] == "legacy-token"
    assert stored_tokens == ["legacy-token", "legacy-token"]
    assert json.loads(config_path.read_text(encoding="utf-8"))["dashboard_api_token"] == ""


def test_corrupt_config_is_preserved_before_defaults_are_written(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(taskLoggerGUI, "CONFIG_FILE", str(config_path))
    monkeypatch.setattr(taskLoggerGUI, "load_dashboard_token", lambda: "stored-token")
    monkeypatch.setattr(taskLoggerGUI, "save_dashboard_token", lambda _token: None)

    loaded = taskLoggerGUI.load_config()
    recovery_files = list(tmp_path.glob("config.recovery-*.json"))

    assert loaded["dashboard_api_token"] == "stored-token"
    assert loaded["_config_recovery_warning"]
    assert len(recovery_files) == 1
    assert recovery_files[0].read_text(encoding="utf-8") == "{broken"
