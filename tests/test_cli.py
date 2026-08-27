import pytest

from spg.cli import main


def test_cli_status_loads_settings_and_bootstraps(monkeypatch, capsys) -> None:
    monkeypatch.setenv("SPG_RUNTIME_PROFILE", "test-fvs")

    exit_code = main(["status"])

    assert exit_code == 0
    assert capsys.readouterr().out.splitlines() == [
        "application=SPG Runtime",
        "foundation=ready",
        "runtime_profile=test-fvs",
    ]


def test_cli_help_exits_successfully(capsys) -> None:
    with pytest.raises(SystemExit) as result:
        main(["--help"])

    assert result.value.code == 0
    assert "Software Production Governor runtime foundation" in capsys.readouterr().out


def test_cli_database_check_requires_configuration(monkeypatch, capsys) -> None:
    monkeypatch.delenv("SPG_DATABASE_URL", raising=False)

    exit_code = main(["db", "check"])

    assert exit_code == 1
    assert "SPG_DATABASE_URL is required" in capsys.readouterr().err
