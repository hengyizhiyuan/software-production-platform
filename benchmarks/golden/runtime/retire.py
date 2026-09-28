"""Retire a completed qualification Preview while preserving durable evidence.

This infrastructure cleanup never changes Watt Work, Candidate, database rows or
volumes. The retirement record explicitly ends availability of this old Preview.
"""
import argparse
import json
from pathlib import Path
import subprocess
import uuid


def docker(*arguments):
    return subprocess.run(['docker', *arguments], check=True, capture_output=True, text=True).stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.directory/'runtime-retirement.json'
    pending = args.directory/'runtime-retirement.pending.json'
    if output.exists():
        raise SystemExit('Already retired; evidence is immutable')
    latest = args.directory/'latest.json'
    try:
        state = json.loads(latest.read_text(encoding='utf-8'))
    except UnicodeDecodeError:
        state = json.loads(latest.read_text(encoding='gbk'))
    session = state.get('preview', {}).get('session') or {}
    if session.get('status') not in {'READY', 'FAILED'}:
        raise SystemExit('Only completed qualification runtimes may be retired')
    identity = uuid.UUID(session['id']).hex
    prefix = 'watt-candidate-preview-'+identity
    containers = docker('ps', '-a', '--format', '{{.Names}}').splitlines()
    selected = [name for name in containers if name.startswith(prefix+'-')
        and docker('inspect', '--format',
            '{{index .Config.Labels "watt.candidate-preview"}}', name).strip() == session['id']]
    inventory = []
    for name in selected:
        details = docker('inspect', '--format',
            '{{json .State}}\n{{json .Mounts}}\n{{json .NetworkSettings.Networks}}', name).splitlines()
        inventory.append({'name': name, 'state': json.loads(details[0]),
            'mounts': json.loads(details[1]), 'networks': json.loads(details[2])})
    record = {'preview_id': session['id'], 'completed_qualification': True,
        'prior_status': session['status'], 'preserve_all_volumes': True,
        'work_or_database_changes': False, 'containers': inventory,
        'endpoint_available_after_retirement': False}
    if pending.exists():
        original = json.loads(pending.read_text(encoding='utf-8'))
        if original.get('preview_id') != session['id']:
            raise SystemExit('Pending retirement evidence belongs to another Preview')
    else:
        pending.write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    if selected:
        docker('stop', '--time', '3', *selected)
        docker('rm', *selected)
    for name in docker('network', 'ls', '--format', '{{.Name}}').splitlines():
        if name.startswith(prefix+'-'):
            label = docker('network', 'inspect', '--format',
                '{{index .Labels "watt.candidate-preview"}}', name).strip()
            if label == session['id']:
                docker('network', 'rm', name)
    pending.replace(output)
    print(json.dumps({'preview_id': session['id'], 'retired': True, 'volumes_preserved': True}))


if __name__ == '__main__':
    main()
