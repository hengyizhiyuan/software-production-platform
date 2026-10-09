"""Task-specific C3 private checkpoint; default is a static plan with no contact.

Python 3.6 host control. Execution is authorized only after the root agent has
finished C3 qualification/collection. Never creates/resumes Work or Human authority,
changes external Git, kills Native containers, restarts resources, or cleans data.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import sys
import tarfile
import uuid

ROOT = Path('/data/watt/c3-semantic-convergence-20261009')
RETRY = ROOT / 'retry-1'
SCHEMA = 'c3-private-recovery-checkpoint-v1'
QUAL = 'C3-semantic-convergence'
RETRY_QUAL = QUAL + '-retry1'
OLD_IMAGE = 'sha256:54355780b7fdd683332b9f9e607b76fcbbfc69f2bf5c42d9a1f888e8acbb4bb3'
PG_NAME = 'watt-c3-postgres-20261009'
GITEA_NAME = 'watt-c3-gitea-20261009'
FIXTURE_NAME = 'watt-c3-retry1-fixture-postgres-20261009'
VOLUMES = ('watt-c3-workspaces-20261009', 'watt-c3-retry1-workspaces-20261009')
NETWORKS = ('watt-c3-control-20261009', 'watt-c3-executor-20261009')
DBS = ('spg_c3_qualification_20261009', 'c3_contract_regression',
       'spg_c3_retry1_qualification_20261009', 'c1_contract_continuity',
       'c3_independent_holdout_20261009')
OPTIONAL_DB = 'c3_contract_regression'
FIXTURE_DB = 'c1_contract_continuity'
ROLES = ('api', 'coordinator', 'worker', 'tool-host')
CONTROL_QUALS = ('C3-development', 'C3-final-image-regression',
                 'C3-final-image-supplemental-fixture', 'C3-retry1-final-image-regression')
STATE = {'phase': 'PREPARE', 'command_ordinal': 0, 'stopped_container_ids': []}
PRIVATE = None


class Blocked(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def require(condition, code):
    if not condition:
        raise Blocked(code)


def within(path, parent):
    path, parent = Path(path), Path(parent)
    return path == parent or parent in path.parents


def no_symlink_ancestors(path):
    path = Path(path)
    for part in (path,) + tuple(path.parents):
        require(not part.is_symlink(), 'SYMLINK_SCOPE_REJECTED')
    require(path.resolve() == path, 'NONCANONICAL_SCOPE_REJECTED')


def private_file(path):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    return os.fdopen(fd, 'wb')


def write_json(path, data, public=False):
    payload = (json.dumps(data, indent=2, sort_keys=True) + '\n').encode('utf-8')
    with private_file(path) as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if public:
        os.chmod(str(path), 0o644)


def digest_file(path):
    digest = sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def call(args, destination=None):
    # No shell/string commands or ENV/credentials are passed on argv. Raw stderr
    # may include private owner data and is retained privately, never printed.
    STATE['command_ordinal'] += 1
    number = STATE['command_ordinal']
    with private_file(PRIVATE / ('command-%04d.stderr' % number)) as error:
        if destination is None:
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=error)
            output = result.stdout
        else:
            with private_file(destination) as stream:
                result = subprocess.run(args, stdout=stream, stderr=error)
                stream.flush()
                os.fsync(stream.fileno())
            output = b''
    require(result.returncode == 0, 'CHECKPOINT_COMMAND_FAILED')
    return output


def parsed(args):
    return json.loads(call(args).decode('utf-8'))


def read_receipt(path):
    no_symlink_ancestors(path)
    require(path.is_file(), 'REQUIRED_C3_RECEIPT_MISSING')
    return json.loads(path.read_text(encoding='utf-8'))


def inspect_container(name, expected_id, expected_image, qualification):
    data = parsed(['docker', 'inspect', name])[0]
    labels = data.get('Config', {}).get('Labels') or {}
    require(data['Id'] == expected_id and data['Image'] == expected_image,
            'C3_CONTAINER_IDENTITY_CHANGED')
    require(data['Name'] == '/' + name and labels.get('watt.production') == 'false'
            and labels.get('watt.qualification') == qualification,
            'C3_CONTAINER_AUTHORITY_SCOPE_MISMATCH')
    require(re.fullmatch(r'[0-9a-f]{64}', data['Id']) is not None
            and re.fullmatch(r'sha256:[0-9a-f]{64}', data['Image']) is not None,
            'INVALID_IMMUTABLE_DOCKER_IDENTITY')
    require(not data['State'].get('Paused') and not data['State'].get('Restarting'),
            'C3_CONTAINER_UNSTABLE_STATE')
    return data


def external_checkout():
    prefix = ['git', '--no-optional-locks', '-C', '/data/watt/runtime/source']
    head = call(prefix + ['rev-parse', 'HEAD']).decode().strip()
    branch = call(prefix + ['rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()
    main_ref = call(prefix + ['rev-parse', 'refs/heads/main']).decode().strip()
    dirty = bool(call(prefix + ['status', '--porcelain']))
    require(all(re.fullmatch(r'[0-9a-f]{40}', value) for value in (head, main_ref)),
            'EXTERNAL_GIT_OBSERVATION_INVALID')
    # Current branch is external reality, never assumed to be canonical main.
    return {'head': head, 'branch': None if branch == 'HEAD' else branch,
            'dirty': dirty, 'refs_heads_main': main_ref}


def outside_states(excluded):
    result = {}
    for cid in call(['docker', 'ps', '-aq', '--no-trunc']).decode().splitlines():
        if cid not in excluded:
            row = parsed(['docker', 'inspect', '--format', '{{json .State}}', cid])
            result[cid] = {'status': row.get('Status'), 'running': row.get('Running'),
                           'paused': row.get('Paused'), 'restarting': row.get('Restarting')}
    return result


def validate_mounts(container, volumes):
    has_scoped_data = False
    for mount in container.get('Mounts', []):
        if mount.get('Type') == 'bind':
            source = Path(mount['Source'])
            if str(source) == '/var/run/docker.sock':
                continue  # host service capability; record only, never archive
            require(within(source, ROOT), 'C3_MOUNT_OUTSIDE_APPROVED_ROOT')
            no_symlink_ancestors(source)
            require(source.exists() and source.stat().st_dev == ROOT.stat().st_dev,
                    'C3_BIND_MOUNT_NOT_COVERED_BY_ROOT_ARCHIVE')
            has_scoped_data = True
        elif mount.get('Type') == 'volume':
            require(mount.get('Name') in volumes, 'C3_UNDECLARED_VOLUME_MOUNT')
            require(mount.get('Source') == volumes[mount['Name']]['Mountpoint'],
                    'C3_VOLUME_MOUNT_IDENTITY_CHANGED')
            has_scoped_data = True
        else:
            raise Blocked('C3_UNSUPPORTED_PERSISTENT_MOUNT')
    require(has_scoped_data, 'C3_PERSISTENT_MOUNTS_MISSING')


def scoped_containers(known, volumes):
    rows = {}
    for cid in call(['docker', 'ps', '-aq', '--no-trunc']).decode().splitlines():
        row = parsed(['docker', 'inspect', cid])[0]
        touches = any((m.get('Type') == 'volume' and m.get('Name') in volumes)
                      or (m.get('Type') == 'bind' and within(m.get('Source', '/'), ROOT))
                      for m in row.get('Mounts', []))
        if cid in known or touches:
            if cid not in known:
                require(not row['State'].get('Running') and not row['State'].get('Paused')
                        and not row['State'].get('Restarting'),
                        'ACTIVE_NATIVE_OR_UNKNOWN_C3_WRITER_REQUIRES_OWNER_STOP')
                labels = row.get('Config', {}).get('Labels') or {}
                require(labels.get('watt.qualification') in (QUAL, RETRY_QUAL) + CONTROL_QUALS
                        or labels.get('watt.production-environment'),
                        'UNKNOWN_CONTAINER_TOUCHES_C3_DATA')
                # Historic test/control metadata may reference existing C2 code
                # read-only. Never archive or change that external mount. Only
                # actual C3 persistent roots/volumes are recovery data.
                if labels.get('watt.production-environment'):
                    validate_mounts(row, volumes)
                    require(row.get('HostConfig', {}).get('ReadonlyRootfs') is True,
                            'NATIVE_WRITABLE_LAYER_NOT_COVERED')
                else:
                    require(labels.get('watt.production') == 'false',
                            'CONTROL_CONTAINER_NOT_ISOLATED')
                    for mount in row.get('Mounts', []):
                        if mount.get('Type') == 'volume':
                            require(mount.get('Name') in volumes, 'CONTROL_UNDECLARED_VOLUME')
                        elif mount.get('Type') == 'bind':
                            source = Path(mount['Source'])
                            require(within(source, ROOT) or mount.get('RW') is False,
                                    'CONTROL_EXTERNAL_WRITABLE_MOUNT_REJECTED')
                        else:
                            raise Blocked('CONTROL_UNSUPPORTED_PERSISTENT_MOUNT')
            rows[cid] = row
    require(set(known).issubset(rows), 'LOCKED_CONTAINER_MISSING')
    return rows



def same_mounts(actual, expected):
    """Docker may reorder Mounts; compare all typed values and multiplicities."""
    if (not isinstance(actual, list) or not isinstance(expected, list)
            or len(actual) != len(expected)
            or any(not isinstance(row, dict) for row in actual + expected)):
        return False
    return sorted(json.dumps(row, sort_keys=True, ensure_ascii=False)
                  for row in actual) == sorted(
                      json.dumps(row, sort_keys=True, ensure_ascii=False)
                      for row in expected)


def read_scope():
    original = read_receipt(ROOT / 'evidence/isolation-preparation.json')
    dependency = read_receipt(ROOT / 'evidence/runtime-dependency-preparation.json')
    retry = read_receipt(RETRY / 'evidence/isolation-preparation.json')
    require(original.get('schema') == 'c3-isolated-preparation-v1'
            and original.get('qualification_root') == str(ROOT)
            and retry.get('schema') == 'c3-retry1-isolated-preparation-v1'
            and retry.get('qualification_root') == str(RETRY)
            and retry.get('preserved_original_root') == str(ROOT), 'C3_SCOPE_RECEIPT_INVALID')
    require((original['new_database'], original['test_database']) == DBS[:2]
            and retry['new_database'] == DBS[2]
            and retry['new_regression_database'] == FIXTURE_DB
            and retry['fixture_postgres_name'] == FIXTURE_NAME
            and dependency['workspace_volume'] == VOLUMES[0]
            and retry['workspace_volume'] == VOLUMES[1], 'C3_DATABASE_OR_VOLUME_SCOPE_CHANGED')
    app = []
    sources = {}
    for root, prefix, qualification, db in (
            (ROOT, 'watt-c3-', QUAL, DBS[0]), (RETRY, 'watt-c3-retry1-', RETRY_QUAL, DBS[2])):
        role_receipt = read_receipt(root / 'evidence/runtime-role-preparation.json')
        identity = read_receipt(root / 'evidence/driver-runtime-identity.json')
        build = read_receipt(root / 'evidence/build.json')
        require(identity.get('isolated') is True and identity.get('qualification') == 'C3'
                and identity.get('database_name') == db and role_receipt.get('database') == db
                and build['exit_code'] == 0 and identity['image_id'] == build['image']['Id']
                and identity['source_revision'] == build['sources']['watt']['revision']
                and role_receipt['source_revision'] == identity['source_revision'],
                'C3_RUNTIME_BUILD_SOURCE_IDENTITY_MISMATCH')
        require(set(r['role'] for r in role_receipt['roles']) == set(ROLES)
                and len(role_receipt['roles']) == len(ROLES), 'C3_ROLE_RECEIPT_INCOMPLETE')
        for role in role_receipt['roles']:
            name = prefix + role['role'] + '-20261009'
            require(role['name'] == name and role['image_id'] == identity['image_id'],
                    'C3_ROLE_VERSION_MISMATCH')
            row = inspect_container(name, role['container_id'], role['image_id'], qualification)
            require(row['Config']['User'] == '10001:10001'
                    and row['HostConfig']['ReadonlyRootfs'] is True
                    and same_mounts(row['Mounts'], role['mounts']), 'C3_APP_PERMISSION_OR_MOUNT_CHANGED')
            app.append(row)
        sources[str(root)] = build['sources']
    require(sources[str(ROOT)]['watt']['revision'] == '390fa22ec24cbab33f7feeeef96f0dfec9ce22f2',
            'ORIGINAL_C3_SOURCE_RECEIPT_CHANGED')
    require(app[0]['Image'] == OLD_IMAGE, 'ORIGINAL_C3_IMAGE_CHANGED')
    pg = inspect_container(PG_NAME, original['postgres_container_id'], original['postgres_image_id'], QUAL)
    gitea = inspect_container(GITEA_NAME, dependency['gitea_container_id'], dependency['gitea_image_id'], QUAL)
    fixture = inspect_container(FIXTURE_NAME, retry['fixture_postgres_container_id'],
                                retry['fixture_postgres_image_id'], RETRY_QUAL)
    shared = {r['name']: r for r in retry['shared_dependencies'] if 'container_id' in r}
    for row in (pg, gitea):
        receipt = shared.get(row['Name'][1:]) or {}
        require(receipt.get('container_id') == row['Id'] and receipt.get('image_id') == row['Image'],
                'C3_SHARED_DEPENDENCY_VERSION_MISMATCH')
    volumes = {}
    for name, qualification in zip(VOLUMES, (QUAL, RETRY_QUAL)):
        row = parsed(['docker', 'volume', 'inspect', name])[0]
        require(row['Name'] == name and row['Labels'].get('watt.production') == 'false'
                and row['Labels'].get('watt.qualification') == qualification,
                'C3_VOLUME_AUTHORITY_MISMATCH')
        mountpoint = Path(row['Mountpoint'])
        no_symlink_ancestors(mountpoint)
        require(str(mountpoint).endswith('/volumes/' + name + '/_data') and mountpoint.is_dir(),
                'C3_VOLUME_PATH_NOT_CANONICAL')
        volumes[name] = row
    networks = {}
    for name in NETWORKS:
        row = parsed(['docker', 'network', 'inspect', name])[0]
        require(row['Name'] == name and row['Labels'].get('watt.production') == 'false'
                and row['Labels'].get('watt.qualification') == QUAL, 'C3_NETWORK_SCOPE_MISMATCH')
        networks[name] = row
    dependencies = (pg, gitea, fixture)
    for row in app + list(dependencies):
        validate_mounts(row, volumes)
    require(all(any(m.get('Destination') == target for m in row['Mounts'])
                for row, target in ((pg, '/var/lib/postgresql/data'),
                                    (fixture, '/var/lib/postgresql/data'), (gitea, '/var/lib/gitea'))),
            'C3_DATABASE_PERSISTENT_MOUNT_MISSING')
    return app, dependencies, volumes, networks, sources


def database_scope(dependencies):
    pg, _, fixture = dependencies
    require(pg['State'].get('Running') is True and fixture['State'].get('Running') is True,
            'C3_POSTGRES_MUST_BE_RUNNING_FOR_DUMP')
    query = 'SELECT datname FROM pg_database WHERE NOT datistemplate'
    def names(owner):
        return call(['docker', 'exec', owner['Id'], 'psql', '-X', '-U', 'c3_app', '-d', 'postgres',
                     '-At', '-v', 'ON_ERROR_STOP=1', '-c', query]).decode().splitlines()
    actual_dbs = names(pg)
    require(set(actual_dbs).issubset(set(DBS) | {'postgres'})
            and (set(DBS) - {OPTIONAL_DB}).issubset(actual_dbs),
            'C3_UNDECLARED_OR_MISSING_REQUIRED_DATABASE')
    fixture_dbs = names(fixture)
    require(set(fixture_dbs) == {FIXTURE_DB, 'postgres'}, 'C3_FIXTURE_DATABASE_SCOPE_CHANGED')
    return sorted(actual_dbs), sorted(fixture_dbs)


def stop_exact(rows):
    ids = [r['Id'] for r in rows if r['State'].get('Running')]
    if ids:
        call(['docker', 'stop', '--time', '30'] + ids)
        STATE['stopped_container_ids'].extend(ids)
    for row in rows:
        current = parsed(['docker', 'inspect', row['Id']])[0]
        require(current['Id'] == row['Id'] and current['Image'] == row['Image']
                and current['State'].get('Running') is False
                and current['State'].get('Paused') is False, 'C3_QUIESCENCE_NOT_CONFIRMED')


def database_checkpoint(container, database):
    cid = container['Id']
    require(container['State'].get('Running') is True, 'C3_POSTGRES_MUST_BE_RUNNING_FOR_DUMP')
    count = call(['docker', 'exec', cid, 'psql', '-X', '-U', 'c3_app', '-d', database,
                  '-At', '-v', 'ON_ERROR_STOP=1', '-c',
                  "SELECT count(*) FROM pg_stat_activity WHERE backend_type='client backend' "
                  'AND pid<>pg_backend_pid() AND datname=current_database()']).decode().strip()
    require(count == '0', 'C3_DATABASE_HAS_ACTIVE_CLIENT_REQUIRES_OWNER_QUIESCENCE')
    prefix = 'retry-fixture-' if cid == STATE.get('fixture_postgres_id') else 'c3-main-'
    has_migration = call(['docker', 'exec', cid, 'psql', '-X', '-U', 'c3_app', '-d', database,
                          '-At', '-v', 'ON_ERROR_STOP=1', '-c',
                          "SELECT to_regclass('public.alembic_version') IS NOT NULL"]).decode().strip()
    require(has_migration in ('t', 'f'), 'C3_MIGRATION_HEAD_OBSERVATION_INVALID')
    migration_head = []
    if has_migration == 't':
        migration_head = call(['docker', 'exec', cid, 'psql', '-X', '-U', 'c3_app', '-d', database,
                               '-At', '-v', 'ON_ERROR_STOP=1', '-c',
                               'SELECT version_num FROM alembic_version ORDER BY version_num']).decode().splitlines()
        require(all(re.fullmatch(r'[A-Za-z0-9_-]+', value) for value in migration_head),
                'C3_MIGRATION_HEAD_VALUE_INVALID')
    leader_error = private_file(PRIVATE / (prefix + database + '-snapshot.stderr'))
    leader = subprocess.Popen(['docker', 'exec', '-i', cid, 'psql', '-X', '-q', '-t', '-A',
                               '-U', 'c3_app', '-d', database, '-v', 'ON_ERROR_STOP=1'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=leader_error)
    try:
        query = ("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n"
                 "SELECT json_build_object('snapshot',pg_export_snapshot(),"
                 "'captured_at',clock_timestamp(),'transaction_snapshot',txid_current_snapshot())::text;\n")
        leader.stdin.write(query.encode('utf-8'))
        leader.stdin.flush()
        ready, _, _ = select.select([leader.stdout], [], [], 30)
        require(bool(ready), 'C3_SNAPSHOT_EXPORT_UNAVAILABLE')
        observation = json.loads(leader.stdout.readline().decode('utf-8'))
        snapshot = observation['snapshot']
        require(re.fullmatch(r'[0-9A-Fa-f-]+', snapshot) is not None,
                'C3_SNAPSHOT_IDENTITY_INVALID')
        prefix = 'retry-fixture-' if cid == STATE.get('fixture_postgres_id') else 'c3-main-'
        destination = PRIVATE / (prefix + database + '.dump')
        began = now()
        call(['docker', 'exec', cid, 'pg_dump', '-U', 'c3_app', '-d', database,
              '--format=custom', '--snapshot=' + snapshot], destination)
        leader.stdin.write(b'COMMIT;\n')
        leader.stdin.close()
        require(leader.wait(timeout=30) == 0, 'C3_SNAPSHOT_TRANSACTION_NOT_CLOSED')
        with destination.open('rb') as stream:
            require(stream.read(5) == b'PGDMP', 'C3_DUMP_FORMAT_INVALID')
        # Validate pg_restore's directory without restoring or creating a DB.
        STATE['command_ordinal'] += 1
        with destination.open('rb') as source, private_file(PRIVATE / (prefix + database + '-restore-list.raw')) as listing, \
                private_file(PRIVATE / (prefix + database + '-restore-list.stderr')) as error:
            result = subprocess.run(['docker', 'exec', '-i', cid, 'pg_restore', '--list'],
                                    stdin=source, stdout=listing, stderr=error)
        require(result.returncode == 0, 'C3_DUMP_DIRECTORY_INVALID')
        return {'database': database, 'present': True, 'status': 'CONSISTENT_DUMP_CAPTURED',
                'migration_head': migration_head, 'container_id': cid, 'started_at': began,
                'ended_at': now(), 'snapshot_observed_at': observation['captured_at'],
                'sha256': digest_file(destination), 'bytes': destination.stat().st_size,
                'directory_readable': True, 'restoration_exercised': False}
    finally:
        if leader.poll() is None:
            # Terminate only the read-only snapshot control process, never PG or Work.
            leader.terminate()
            try:
                leader.wait(timeout=10)
            except subprocess.TimeoutExpired:
                leader.kill()
                leader.wait()
        leader_error.close()


def archive_integrity(path, image=False):
    count = 0
    image_manifest = None
    with tarfile.open(str(path), 'r:') as archive:
        for entry in archive:
            count += 1
            require(not entry.name.startswith('/') and '..' not in Path(entry.name).parts,
                    'C3_ARCHIVE_PATH_INVALID')
            if image and entry.name == 'manifest.json':
                image_manifest = json.load(archive.extractfile(entry))
    require(count > 0 and (not image or isinstance(image_manifest, list)),
            'C3_ARCHIVE_DIRECTORY_INVALID')
    return {'sha256': digest_file(path), 'bytes': path.stat().st_size,
            'archive_directory_readable': True, 'member_count': count}


def execute():
    global PRIVATE
    require(sys.platform.startswith('linux') and os.geteuid() == 0, 'C3_HOST_ROOT_REQUIRED')
    os.umask(0o077)
    for path in (ROOT, RETRY, ROOT / 'private', RETRY / 'private', ROOT / 'evidence'):
        no_symlink_ancestors(path)
        require(path.is_dir(), 'APPROVED_C3_DIRECTORY_MISSING')
    require((ROOT / 'private').stat().st_mode & 0o077 == 0
            and (RETRY / 'private').stat().st_mode & 0o077 == 0, 'C3_PRIVATE_ROOT_MODE_INVALID')
    checkpoint_parent = ROOT / 'private/checkpoints'
    no_symlink_ancestors(checkpoint_parent)
    checkpoint_parent.mkdir(mode=0o700, exist_ok=True)
    require(checkpoint_parent.stat().st_mode & 0o077 == 0, 'C3_CHECKPOINT_PARENT_MODE_INVALID')
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex
    PRIVATE = checkpoint_parent / name
    PRIVATE.mkdir(mode=0o700)
    STATE['started_at'] = now()
    STATE['phase'] = 'VERIFY_EXACT_SCOPE'
    app, dependencies, volumes, networks, sources = read_scope()
    observed_database_scope = database_scope(dependencies)
    known = {row['Id'] for row in app + list(dependencies)}
    all_scoped = scoped_containers(known, volumes)
    images = sorted({row['Image'] for row in all_scoped.values()} | {OLD_IMAGE})
    image_inspects = parsed(['docker', 'image', 'inspect'] + images)
    require({row['Id'] for row in image_inspects} == set(images), 'C3_REQUIRED_IMAGE_MISSING')
    before_git = external_checkout()
    before_outside = outside_states(set(all_scoped))
    write_json(PRIVATE / 'scope-inspect.raw.json', {'containers': list(all_scoped.values()),
                'volumes': volumes, 'networks': networks, 'images': image_inspects})
    write_json(PRIVATE / 'outside-before.json', {'checkout': before_git, 'containers': before_outside})
    root_bytes = int(call(['du', '-sb', '--exclude=*/private/checkpoints', str(ROOT)]).decode().split()[0])
    volume_bytes = sum(int(call(['du', '-sb', row['Mountpoint']]).decode().split()[0]) for row in volumes.values())
    # Conservative: full root+volumes, logical SQL dump headroom, unshared image
    # layer sizes counted per image, plus 1GiB. No cleanup when unavailable.
    required = (root_bytes + volume_bytes) * 3 + sum(row['Size'] for row in image_inspects) * 2 + 1024 ** 3
    free = shutil.disk_usage(str(checkpoint_parent)).free
    require(free >= required, 'C3_CHECKPOINT_DISK_INSUFFICIENT_NO_CLEANUP')
    write_json(PRIVATE / 'plan.raw.json', {'schema': SCHEMA, 'sources': sources,
                'required_bytes_conservative': required, 'free_bytes': free,
                'application_ids': [r['Id'] for r in app], 'dependency_ids': [r['Id'] for r in dependencies],
                'image_ids': images, 'databases': list(DBS) + [FIXTURE_DB]})
    STATE['phase'] = 'QUIESCE_ONLY_C3_APPLICATIONS'
    # Recheck concurrent actors immediately before the first resource mutation.
    require(set(scoped_containers(known, volumes)) == set(all_scoped), 'C3_SCOPE_CHANGED_BEFORE_QUIESCENCE')
    stop_exact(app)
    require(set(scoped_containers(known, volumes)) == set(all_scoped),
            'C3_SCOPE_CHANGED_AFTER_APPLICATION_QUIESCENCE')
    STATE['phase'] = 'CONSISTENT_DATABASE_DUMPS'
    pg, gitea, fixture = dependencies
    actual_dbs, fixture_dbs = database_scope(dependencies)
    require((actual_dbs, fixture_dbs) == observed_database_scope, 'C3_DATABASE_SCOPE_CHANGED_AFTER_QUIESCENCE')
    STATE['fixture_postgres_id'] = fixture['Id']
    dumps = []
    for db in DBS:
        if db in actual_dbs:
            dumps.append(database_checkpoint(pg, db))
        else:
            require(db == OPTIONAL_DB, 'C3_REQUIRED_DUMP_MISSING')
            dumps.append({'database': db, 'container_id': pg['Id'], 'present': False,
                          'status': 'ABSENT_OBSERVED_NO_DUMP', 'migration_head': [], 'observed_at': now()})
    dumps.append(database_checkpoint(fixture, FIXTURE_DB))
    for owner, label in ((pg, 'c3-main'), (fixture, 'c3-fixture')):
        call(['docker', 'exec', owner['Id'], 'pg_dumpall', '-U', 'c3_app', '--globals-only'],
             PRIVATE / (label + '-postgres-roles.sql'))
    write_json(PRIVATE / 'database-snapshot-observations.json', dumps)
    STATE['phase'] = 'COLD_STOP_ONLY_C3_DEPENDENCIES'
    stop_exact(dependencies)
    cold_containers = scoped_containers(known, volumes)
    require(set(cold_containers) == set(all_scoped), 'C3_SCOPE_CHANGED_BEFORE_ARCHIVE')
    require(all(not row['State'].get('Running') and not row['State'].get('Paused')
                for row in cold_containers.values()), 'C3_WRITER_RESTARTED_BEFORE_COLD_ARCHIVE')
    STATE['phase'] = 'COLD_ARCHIVE_PRIVATE_DATA'
    root_archive = PRIVATE / 'c3-original-and-retry-root.tar'
    call(['tar', '--numeric-owner', '--one-file-system', '--exclude=./private/checkpoints',
          '-C', str(ROOT), '-cf', '-', '.'], root_archive)
    archives = {'root': archive_integrity(root_archive)}
    for volume, row in volumes.items():
        destination = PRIVATE / (volume + '.tar')
        call(['tar', '--numeric-owner', '--one-file-system', '-C', row['Mountpoint'], '-cf', '-', '.'], destination)
        archives[volume] = archive_integrity(destination)
    image_archive = PRIVATE / 'c3-exact-images.tar'
    call(['docker', 'image', 'save'] + images, image_archive)
    archives['images'] = archive_integrity(image_archive, image=True)
    STATE['phase'] = 'VERIFY_PRESERVATION'
    final_containers = scoped_containers(known, volumes)
    require(set(final_containers) == set(all_scoped)
            and all(not row['State'].get('Running') and not row['State'].get('Paused')
                    for row in final_containers.values()), 'C3_WRITER_APPEARED_DURING_COLD_ARCHIVE')
    after_git = external_checkout()
    after_outside = outside_states(set(all_scoped))
    outside_same = before_git == after_git and before_outside == after_outside
    public = {'schema': SCHEMA, 'status': 'CAPTURED_PRIVATE' if outside_same else 'CAPTURED_PRIVATE_OUTSIDE_CHANGE_OBSERVED',
              'started_at': STATE['started_at'], 'ended_at': now(), 'private_checkpoint_path': str(PRIVATE),
              'scope_roots': [str(ROOT), str(RETRY)], 'sources': sources,
              'container_ids': sorted(all_scoped), 'quiesced_app_ids': [r['Id'] for r in app],
              'stopped_dependency_ids': [r['Id'] for r in dependencies],
              'image_ids': images, 'workspace_volumes': list(VOLUMES), 'database_dumps': dumps,
              'archives': archives, 'external_checkout_before': before_git, 'external_checkout_after': after_git,
              'outside_container_states_unchanged': before_outside == after_outside,
              'outside_change_origin': 'NOT_OBSERVED' if outside_same else 'UNKNOWN',
              'default_state': 'ONLY_C3_STOPPED_NO_RESTART', 'ephemeral_control_writable_layers_preserved': False,
              'persistent_c3_mount_data_captured': True, 'single_atomic_database_git_filesystem_snapshot': False,
              'database_consistency': 'separate exported read-only snapshot per database after C3 app quiescence',
              'cold_filesystem_capture': True, 'restoration_exercised': False, 'offsite_backup_confirmed': False,
              'work_created_resumed_or_modified': False, 'human_decisions_created': False,
              'model_calls': 0, 'production_or_external_checkout_written': False,
              'harness_sha256': digest_file(Path(__file__))}
    write_json(PRIVATE / 'checkpoint-receipt.json', public)
    write_json(ROOT / 'evidence' / ('private-checkpoint-' + name + '.json'), public, public=True)
    STATE['phase'] = 'COMPLETE'
    print(json.dumps({'schema': SCHEMA, 'status': public['status'], 'receipt': 'private-checkpoint-' + name + '.json',
                      'only_c3_stopped': True, 'restoration_exercised': False, 'credential_values_released': False}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-private-checkpoint', action='store_true')
    args = parser.parse_args()
    if not args.execute_private_checkpoint:
        print(json.dumps({'schema': SCHEMA, 'prepared_only': True, 'scope_roots': [ROOT.as_posix(), RETRY.as_posix()],
              'execute_required': '--execute-private-checkpoint', 'docker_database_network_contact': False,
              'requires_root_safe_checkpoint_after_qualification': True, 'active_native_writer_action': 'BLOCKED',
              'external_checkout_action': 'READ_ONLY_ACTUAL_HEAD_BRANCH_DIRTY_MAIN_REF',
              'restart_cleanup_restore_or_work_action': False}))
        return 0
    try:
        execute()
        return 0
    except Exception as error:
        code = str(error) if isinstance(error, Blocked) else 'CHECKPOINT_CONTROL_EXCEPTION'
        if PRIVATE is not None:
            try:
                write_json(PRIVATE / 'failure.json', {'schema': SCHEMA, 'ended_at': now(), 'state': STATE,
                           'error_type': type(error).__name__, 'code': code, 'automatic_restart_or_cleanup': False})
            except Exception:
                pass  # Disk/permission failure must not leak a raw traceback.
        print(json.dumps({'schema': SCHEMA, 'status': 'BLOCKED_OR_PARTIAL_PRIVATE_CAPTURE', 'error_type': type(error).__name__,
                          'code': code, 'phase': STATE['phase'], 'command_ordinal': STATE['command_ordinal'],
                          'automatic_restart_cleanup_or_work_action': False}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
