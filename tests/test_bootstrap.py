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
        "wic_runtime_mode": "WIC_VNEXT_CONTROLLED",
        "qualified_wic_runtime_mode": "WIC_VNEXT_CONTROLLED",
        "wic_configuration_parity": "PASS",
    }
    assert not workspace_root.exists()
