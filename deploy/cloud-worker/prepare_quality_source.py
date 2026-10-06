"""Create an immutable exact source snapshot for reviewed Quality recipes.

Run from the existing deployment workflow; no cloud/RAM/production state action.
Python 3.6 compatible for the current Alibaba Cloud Linux host.
"""
import argparse
import os
from pathlib import Path
import re
import subprocess


def git(source, *args):
    return subprocess.check_output(['git', '-c', 'safe.directory=' + str(source), '-C', str(source)] + list(args)).decode().strip()


def prepare(source, output_base, uid=10001):
    source = source.resolve()
    if git(source, 'status', '--porcelain'):
        raise RuntimeError('Quality source must be committed and clean')
    revision = git(source, 'rev-parse', 'HEAD')
    if not re.match(r'^[a-f0-9]{40}$', revision):
        raise RuntimeError('Exact source revision is required')
    target = output_base / ('source-' + revision)
    if not target.exists():
        output_base.mkdir(parents=True, exist_ok=True)
        subprocess.check_call(['git', 'clone', '--quiet', '--no-local', '--depth', '1',
            '--branch', git(source, 'branch', '--show-current'), str(source), str(target)])
        # Preserve the canonical source identity, never copy credentials/helper config.
        subprocess.check_call(['git', '-C', str(target), 'remote', 'set-url', 'origin',
            'git@github.com:hengyizhiyuan/software-production-platform.git'])
    if git(target, 'rev-parse', 'HEAD') != revision or git(target, 'rev-parse', 'HEAD^{tree}') != git(source, 'rev-parse', 'HEAD^{tree}'):
        raise RuntimeError('Quality source snapshot differs from qualified source')
    for p in [target] + list(target.rglob('*')):
        if p.is_symlink():
            continue
        if os.geteuid() == 0:
            os.chown(str(p), uid, uid)
        p.chmod(p.stat().st_mode & ~0o222)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-base', type=Path, required=True)
    args = parser.parse_args()
    print(prepare(args.source, args.output_base))
