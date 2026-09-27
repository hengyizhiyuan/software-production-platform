"""Qualification identity only; never reads environment values or credentials."""
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import subprocess


def source_receipt(root: Path):
    files = sorted(p for directory in ('src', 'migrations', 'docker')
        for p in (root / directory).rglob('*') if p.is_file()
        and '__pycache__' not in p.parts and p.suffix != '.pyc'
        and not any(part.endswith('.egg-info') for part in p.parts))
    hashes = {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in files}
    return {'captured_at': datetime.now(UTC).isoformat(),
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'tree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=root, text=True).strip(),
        'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip()),
        'source_hashes': hashes,
        'source_fingerprint': sha256(__import__('json').dumps(hashes, sort_keys=True).encode()).hexdigest()}


def verify_freeze(root: Path, freeze: dict):
    actual = source_receipt(root)
    if actual['source_fingerprint'] != freeze['source_fingerprint']:
        raise ValueError('Implementation changed after freeze; create a new freeze and unseen holdout')
    return actual
