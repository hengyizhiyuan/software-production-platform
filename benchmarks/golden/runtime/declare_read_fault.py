"""Declare the GC-EX-05 no-effect read fault before its Native Attempt starts.

The declaration is qualification infrastructure, not a Work instruction. The
internal token stays inside the proxy container and is never logged here.
"""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import subprocess
import time
from uuid import UUID

if __package__:
    from .journey import ProductClient
else:
    from journey import ProductClient


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--proxy-container', required=True)
    args = parser.parse_args()
    output = args.directory / 'declared-no-effect-read.json'
    if output.exists():
        raise SystemExit('Existing fault declaration is immutable')
    env = dict(line.split('=', 1) for line in args.env_file.read_text(
        encoding='utf-8').splitlines() if '=' in line)
    client = ProductClient(args.base, env['SPG_OPERATOR_TOKEN'])
    started = time.monotonic()
    while time.monotonic() - started < 180:
        journey_path = args.directory / 'journey.json'
        if not journey_path.exists():
            time.sleep(.2)
            continue
        journey = json.loads(journey_path.read_text(encoding='utf-8'))
        if journey['case'] != 'GC-EX-05':
            raise SystemExit('This declaration is authorized only for GC-EX-05')
        interaction = client.request('/api/interactions/' + journey['interaction_id'])
        work_id = interaction.get('governed_work_id')
        if not work_id:
            time.sleep(.2)
            continue
        work_id = str(UUID(work_id))
        evidence_id = f"GC-EX-05:trial-{journey['trial']}"
        code = (
            'import json,os,urllib.request; '
            'payload=json.dumps({"work_id":os.environ["FAULT_WORK_ID"],'
            '"evidence_id":os.environ["FAULT_EVIDENCE_ID"]}).encode(); '
            'request=urllib.request.Request('
            '"http://127.0.0.1:8012/qualification/no-effect-file-read",'
            'data=payload,headers={"Content-Type":"application/json",'
            '"X-Watt-Internal-Token":os.environ["SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN"]}); '
            'print(urllib.request.urlopen(request,timeout=10).read().decode())'
        )
        result = subprocess.run(['docker', 'exec',
            '-e', f'FAULT_WORK_ID={work_id}',
            '-e', f'FAULT_EVIDENCE_ID={evidence_id}',
            args.proxy_container, 'python', '-c', code],
            check=True, capture_output=True, text=True)
        declaration = json.loads(result.stdout)
        if declaration.get('declared') is not True or declaration.get('work_id') != work_id:
            raise SystemExit('Fault proxy did not acknowledge the exact Work declaration')
        record = {'case': 'GC-EX-05', 'trial': journey['trial'],
            'work_id': work_id, 'evidence_id': evidence_id,
            'proxy_acknowledgement': declaration,
            'declared_at': datetime.now(UTC).isoformat(),
            'manual_work_rescue': False, 'source_modified': False}
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n',
            encoding='utf-8')
        print(json.dumps(record, ensure_ascii=False), flush=True)
        return
    raise SystemExit('No governed Work appeared before the fault declaration deadline')


if __name__ == '__main__':
    main()
