from spg.application import bootstrap
from spg.config import Settings


def test_bootstrap_has_no_external_side_effects(tmp_path) -> None:
    workspace_root = tmp_path / "workspaces"
    application = bootstrap(Settings(workspace_root=workspace_root))

    assert application.settings.workspace_root == workspace_root
    assert application.status() == {
        "application": "SPG Runtime",
        "foundation": "ready",
        "runtime_profile": "local-fvs",
    }
    assert not workspace_root.exists()

