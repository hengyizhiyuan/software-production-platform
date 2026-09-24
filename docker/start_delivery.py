"""Isolated Work-to-Delivery acceptance startup; no implicit product repository."""
from pathlib import Path
import os
import subprocess
import sys



def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    run(sys.executable, "-m", "alembic", "upgrade", "head", cwd="/app")
    imports = Path(os.environ.get("SPG_WORKSPACE_ROOT", "/var/lib/spg/workspaces")).parent / "repository-imports"
    imports.mkdir(parents=True, exist_ok=True)
    repository = imports / "inventory-example"
    if not repository.exists():
        repository.mkdir()
        run("git", "init", "-b", "main", str(repository))
        (repository / "README.md").write_text("# Inventory example\n\nSynthetic existing software: an inventory tool for a small operations team.\nCurrent scope: record items and quantities. Planned continuation: review low-stock reminders.\n", encoding="utf-8")
        run("git", "-C", str(repository), "add", "README.md")
        run("git", "-C", str(repository), "-c", "user.name=Watt Acceptance", "-c", "user.email=acceptance@localhost", "commit", "-m", "Synthetic existing repository baseline")
    import uvicorn
    from spg.api import create_http_application
    uvicorn.run(create_http_application(), host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
