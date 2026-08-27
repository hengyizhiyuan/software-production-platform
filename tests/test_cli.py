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
