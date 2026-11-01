from __future__ import annotations

import yaml

from infra_monitor.cli import main
from infra_monitor.storage import SQLiteStore


def write_config(tmp_path):
    config = {
        "database_path": str(tmp_path / "monitoring.db"),
        "export_directory": str(tmp_path / "exports"),
        "assets": [
            {
                "asset_id": "DB-LOCAL",
                "hostname": "local-db",
                "asset_type": "Database",
            }
        ],
        "collectors": {
            "system": {"enabled": False},
            "sqlite": [
                {
                    "asset_id": "DB-LOCAL",
                    "database_path": str(tmp_path / "application.db"),
                }
            ],
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_cli_end_to_end(tmp_path, capsys):
    config = write_config(tmp_path)
    prefix = ["--config", str(config)]

    assert main([*prefix, "init-db"]) == 0
    assert main([*prefix, "monitor", "--cycles", "1", "--interval", "0"]) == 0
    assert main([*prefix, "demo", "--cycles", "6", "--reset"]) == 0
    assert main([*prefix, "incidents"]) == 0
    assert main([*prefix, "export"]) == 0

    store = SQLiteStore(tmp_path / "monitoring.db")
    incident_id = store.query(
        """
        SELECT incident_id FROM incidents
        WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'ESCALATED')
        LIMIT 1
        """
    )[0]["incident_id"]
    assert main([*prefix, "acknowledge", incident_id]) == 0
    assert main([*prefix, "resolve", incident_id, "--note", "Validated recovery"]) == 0
    assert "Demo completed" in capsys.readouterr().out


def test_cli_reports_no_collectors_and_invalid_incident(tmp_path, capsys):
    config = write_config(tmp_path)
    loaded = yaml.safe_load(config.read_text(encoding="utf-8"))
    loaded["collectors"] = {}
    config.write_text(yaml.safe_dump(loaded), encoding="utf-8")
    prefix = ["--config", str(config)]

    assert main([*prefix, "monitor"]) == 2
    assert main([*prefix, "acknowledge", "INC-MISSING"]) == 1
    assert main([*prefix, "resolve", "INC-MISSING", "--note", "none"]) == 1
    assert "not found" in capsys.readouterr().err.lower()


def test_cli_rejects_invalid_cycle_count(tmp_path):
    config = write_config(tmp_path)
    try:
        main(["--config", str(config), "demo", "--cycles", "0"])
    except SystemExit as error:
        assert "at least 1" in str(error)
    else:
        raise AssertionError("Invalid cycle count was accepted")

def test_cli_displays_message_when_no_incidents_exist(tmp_path, capsys):
    config = write_config(tmp_path)
    prefix = ["--config", str(config)]

    assert main([*prefix, "init-db"]) == 0
    assert main([*prefix, "incidents"]) == 0

    output = capsys.readouterr().out
    assert "No incidents found." in output


def test_cli_monitor_waits_between_cycles(tmp_path, monkeypatch):
    config = write_config(tmp_path)
    sleep_calls = []

    monkeypatch.setattr(
        "infra_monitor.cli.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    assert main([
        "--config", str(config),
        "monitor",
        "--cycles", "2",
        "--interval", "1",
    ]) == 0

    assert sleep_calls == [1]


def test_cli_demo_waits_between_cycles(tmp_path, monkeypatch):
    config = write_config(tmp_path)
    sleep_calls = []

    monkeypatch.setattr(
        "infra_monitor.cli.time.sleep",
        lambda seconds: sleep_calls.append(seconds),
    )

    assert main([
        "--config", str(config),
        "demo",
        "--cycles", "2",
        "--interval", "1",
        "--reset",
    ]) == 0

    assert sleep_calls == [1]


def test_main_module_exits_with_cli_return_code(monkeypatch):
    import runpy
    import pytest

    monkeypatch.setattr("infra_monitor.cli.main", lambda: 7)

    with pytest.raises(SystemExit) as error:
        runpy.run_module("infra_monitor.__main__", run_name="__main__")

    assert error.value.code == 7
