#!/usr/bin/env python3
"""Bounded offline backup + isolated restore proof, not a backup scheduler or HA.

Host Python 3.6 compatible. Run as the authorized test ECS operator. Canonical
Compose services pause for one consistent SQL/Git/file cut and then restart.
The isolated restored PostgreSQL has no production Worker or published ports.
Private deployment configuration is referenced, never copied into the archive.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tarfile
import time

RUNTIME = Path('/data/watt/runtime')
SERVICES = ['api', 'native-worker', 'native-coordinator', 'native-tool-host', 'postgres', 'gitea']


def run(args, data=None, env=None):
    result = subprocess.run(args, cwd=str(RUNTIME), input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env)
    if result.returncode:
        # Docker/SQL error bodies may include connection secrets. Emit only
        # command kind and exit code; never forward secret-bearing stderr.
        raise RuntimeError('qualification command failed: {} exit {}'.format(args[0], result.returncode))
    return result.stdout


def compose(*args, **kw):
    return run(['docker', 'compose'] + list(args), **kw)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def fingerprint(root):
    # Files only; symlinks are preserved by tar and not followed to host secrets.
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and not p.is_symlink()}


def main(destination):
    target = Path(destination).resolve()
    if not str(target).startswith('/data/watt/qualifications/') or target.exists():
        raise RuntimeError('Use a new exact qualification directory under /data/watt/qualifications')
    if run(['git', '-C', str(RUNTIME / 'source'), 'status', '--porcelain']).strip():
        raise RuntimeError('Durable source must be clean')
    target.mkdir(parents=True, mode=0o700)
    os.chmod(str(target), 0o700)
    os.umask(0o077)
    state_script = (RUNTIME / 'source/deploy/cloud-worker/qualification_state.py').read_bytes()
    relationship_script = (RUNTIME / 'source/deploy/cloud-worker/qualification_relationships.py').read_bytes()
    started = time.monotonic()
    disk_before = shutil.disk_usage('/data').used
    inspection = json.loads(run(['docker', 'inspect', 'watt-cloud-worker-gitea-1']))[0]
    gitea_data = Path(next(x['Source'] for x in inspection['Mounts'] if x['Destination'] == '/var/lib/gitea'))
    members = {'app': Path('/data/watt/app'), 'native-executor': Path('/data/watt/native-executor'),
               'tool-receipts': Path('/data/watt/tool-receipts'), 'workspaces': Path('/data/watt/workspaces'),
               'gitea': gitea_data}
    # These are deployment credentials, not engineering data. Restoring a new
    # Gitea server requires the existing protected deployment process to supply them.
    def exclude(info):
        parts = Path(info.name).parts
        if '.env' in parts or (parts and parts[0] == 'gitea' and len(parts) > 1 and parts[1] in {'ssh', 'jwt'}):
            return None
        return info
    live_restarted = False
    restore_pg = 'watt-closure-restore-' + secrets.token_hex(4)
    restore_net = restore_pg + '-net'
    try:
        # Worker first; its existing fenced recovery handles an unfinished lease.
        compose('stop', '-t', '30', 'native-worker')
        compose('stop', '-t', '30', 'api', 'native-coordinator', 'native-tool-host', 'gitea')
        cut = time.time()
        before = json.loads(compose('run', '--rm', '--no-deps', '-T', 'api', 'python', '-', data=state_script))
        (target / 'sql-state.json').write_text(json.dumps(before, sort_keys=True))
        with (target / 'postgres.dump').open('wb') as out:
            result = subprocess.run(['docker', 'compose', 'exec', '-T', 'postgres', 'pg_dump',
                                     '-U', 'spg', '-d', 'spg_dev', '-Fc'], cwd=str(RUNTIME), stdout=out, stderr=subprocess.PIPE)
            if result.returncode:
                raise RuntimeError('pg_dump failed')
        source_members = {name: {path: digest for path, digest in fingerprint(source).items()
            if exclude(tarfile.TarInfo(name + '/' + path)) is not None}
            for name, source in members.items()}
        with tarfile.open(str(target / 'runtime.tar.gz'), 'w:gz') as archive:
            for name, source in members.items():
                if not source.is_dir():
                    raise RuntimeError('Required persistent state absent: ' + name)
                archive.add(str(source), arcname=name, recursive=True, filter=exclude)
        backup_done = time.monotonic()
        # All six services now undergo a real interruption, including PostgreSQL.
        compose('stop', '-t', '30', 'postgres')
        stopped = [json.loads(line)['State'] for line in compose('ps', '--all', '--format', 'json').decode().splitlines()
                   if line.strip() and json.loads(line)['Service'] in SERVICES]
        assert len(stopped) == 6 and all(x == 'exited' for x in stopped)
        compose('up', '-d', '--no-build')
        live_restarted = True
        live_restart_done = time.monotonic()
        restored = target / 'restored'
        restored.mkdir(mode=0o700)
        with tarfile.open(str(target / 'runtime.tar.gz'), 'r:gz') as archive:
            for member in archive.getmembers():
                path = (restored / member.name).resolve()
                if not str(path).startswith(str(restored) + '/') or member.isdev() or member.islnk():
                    raise RuntimeError('Unsafe recovery archive member')
                if member.issym():
                    link = (path.parent / member.linkname).resolve()
                    if Path(member.linkname).is_absolute() or not str(link).startswith(str(restored) + '/'):
                        raise RuntimeError('Unsafe recovery archive link')
            archive.extractall(str(restored))
        archive_members = {name: fingerprint(restored / name) for name in members}
        assert archive_members == source_members, 'Restored engineering files differ from the quiesced cut'
        # Restore into an isolated PostgreSQL container/network, with no host port,
        # no shared production data mount, and an ephemeral qualification secret.
        run(['docker', 'network', 'create', '--internal', restore_net])
        password = secrets.token_hex(32)
        env = dict(os.environ, POSTGRES_PASSWORD=password)
        pg_image = json.loads(run(['docker', 'inspect', 'watt-cloud-worker-postgres-1']))[0]['Config']['Image']
        run(['docker', 'run', '-d', '--name', restore_pg, '--network', restore_net,
             '--network-alias', 'restored-postgres', '-e', 'POSTGRES_PASSWORD', '-e', 'POSTGRES_USER=spg',
             '-e', 'POSTGRES_DB=spg_dev', '-v', str(restored / 'postgres') + ':/var/lib/postgresql/data', pg_image], env=env)
        for _ in range(60):
            result = subprocess.run(['docker', 'exec', restore_pg, 'pg_isready', '-U', 'spg', '-d', 'spg_dev'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Isolated PostgreSQL startup unavailable')
        with (target / 'postgres.dump').open('rb') as source:
            result = subprocess.run(['docker', 'exec', '-i', restore_pg, 'pg_restore', '-U', 'spg',
                                     '-d', 'spg_dev', '--exit-on-error', '--no-owner'], stdin=source,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            raise RuntimeError('Isolated pg_restore failed')
        env = dict(os.environ, SPG_DATABASE_URL='postgresql+psycopg://spg:' + password + '@restored-postgres:5432/spg_dev')
        observed = json.loads(run(['docker', 'run', '--rm', '-i', '--network', restore_net,
                                  '-e', 'SPG_DATABASE_URL', 'watt-cloud-worker:local', 'python', '-'],
                                 data=state_script, env=env))
        assert observed == before, 'Restored canonical SQL tables differ from the quiesced cut'
        relationship_env = dict(env, WATT_RESTORED_APP='/restored-app')
        relationships = json.loads(run(['docker', 'run', '--rm', '-i', '--network', restore_net,
            '-e', 'SPG_DATABASE_URL', '-e', 'WATT_RESTORED_APP', '-v', str(restored / 'app') + ':/restored-app:ro',
            'watt-cloud-worker:local', 'python', '-'], data=relationship_script, env=relationship_env))
        # Database→Git identity check against restored bare repos, independent of
        # the running production Gitea process or repository HEAD inference.
        read_sources = b"from spg.config import Settings\nfrom spg.infrastructure.persistence import Database\nfrom sqlalchemy import text\nimport json\nd=Database.from_settings(Settings())\nwith d.unit_of_work() as u: print(json.dumps([dict(r) for r in u.session.execute(text('select provider_reference,accepted_revision,accepted_tree from product_managed_sources')).mappings()]))\nd.dispose()\n"
        sources = json.loads(run(['docker', 'run', '--rm', '-i', '--network', restore_net,
                                 '-e', 'SPG_DATABASE_URL', 'watt-cloud-worker:local', 'python', '-'], data=read_sources, env=env))
        repositories = list((restored / 'gitea').rglob('*.git'))
        for source in sources:
            bare = next(p for p in repositories if p.name == source['provider_reference'].lower() + '.git')
            ref = run(['git', '--git-dir=' + str(bare), 'rev-parse', 'refs/heads/accepted']).decode().strip()
            tree = run(['git', '--git-dir=' + str(bare), 'rev-parse', source['accepted_revision'] + '^{tree}']).decode().strip()
            assert (ref, tree) == (source['accepted_revision'], source['accepted_tree'])
        # The extraction must have preserved every archived engineering file.
        assert all(fingerprint(restored / name) == hashes for name, hashes in archive_members.items())
        manifest = {'source_head': run(['git', '-C', str(RUNTIME / 'source'), 'rev-parse', 'HEAD']).decode().strip(),
                    'migration': relationships['migration'], 'restored_relationships': relationships, 'consistent_cut_epoch': cut,
                    'sql_table_count': len(before), 'sql_rows': sum(r['rows'] for r in before.values()),
                    'restored_managed_sources': len(sources), 'restored_file_count': sum(len(x) for x in archive_members.values()),
                    'backup_seconds': round(backup_done - started, 3),
                    'live_full_restart_seconds': round(live_restart_done - backup_done, 3),
                    'isolated_restore_seconds': round(time.monotonic() - live_restart_done, 3),
                    'observed_rpo': 'zero acknowledged writes after the quiesced cut; not an SLA',
                    'configuration_references': ['/data/watt/runtime/.env', '/data/watt/runtime/docker-compose.yml',
                        'protected Gitea config and SSH/JWT keys via deployment process', 'Git-pinned ECF/Guardian source'],
                    'excluded_credentials': ['.env', 'gitea/ssh', 'gitea/jwt', 'gitea configuration'],
                    'archives': {name: {'sha256': sha(target / name), 'bytes': (target / name).stat().st_size}
                                 for name in ['postgres.dump', 'runtime.tar.gz']},
                    'disk_used_before': disk_before, 'disk_used_after': shutil.disk_usage('/data').used,
                    'full_stop_services': SERVICES, 'sql_equal': True, 'git_equal': True, 'file_equal': True,
                    'restore_worker_started': False, 'public_ports_added': 0}
        (target / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2))
        (target / 'file-hashes.json').write_text(json.dumps(archive_members, sort_keys=True))
        print(json.dumps(manifest, sort_keys=True))
    finally:
        if not live_restarted:
            compose('up', '-d', '--no-build')
        subprocess.run(['docker', 'rm', '-f', restore_pg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(['docker', 'network', 'rm', restore_net], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # The isolated restored directory + restricted archives remain as evidence.


if __name__ == '__main__':
    main(sys.argv[1])
