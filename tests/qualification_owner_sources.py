"""Locate real externally configured owner source without synthesizing packages."""
from importlib.util import find_spec
from pathlib import Path


def owner_source_root(owner: str, fallback: Path) -> Path:
    try:
        spec = find_spec(f"{owner}.runtime")
    except (ImportError,ModuleNotFoundError):
        spec = None
    if spec is not None and spec.origin:
        origin = Path(spec.origin)
        if origin.is_file() and origin.suffix == ".py":
            return origin.parents[2] if origin.name == "__init__.py" else origin.parents[1]
    return fallback
