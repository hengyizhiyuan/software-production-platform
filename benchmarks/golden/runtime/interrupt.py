"""Inject one declared Worker loss after a settled production checkpoint.

Observe lease/receipts read-only; stop only the Worker owning this declared case.
The coordinator and peer Worker must recover it without a turn, retry, state
repair, source edit or Preview-start action. The stopped process is restarted
only after this trial ends, as infrastructure cleanup rather than Work rescue.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    output = args.directory/'worker-interruption.json'
    if output.exists():
        raise SystemExit('Existing fault evidence is immutable')
    env = dict(line.split('=', 1) for line in args.env_file.read_text(encoding='utf-8').splitlines() if '=' in line)
    client = ProductClient(args.base, env['SPG_OPERATOR_TOKEN'])
    started = time.monotonic()
    while time.monotonic()-started < 1200:
        if not (args.directory/'journey.json').exists():
            time.sleep(.5)
            continue
        journey = json.loads((args.directory/'journey.json').read_text(encoding='utf-8'))
        corpus = json.loads((Path(__file__).resolve().parents[1]/'tier0-v1.json').read_text(encoding='utf-8'))
        case = next(item for item in corpus['cases'] if item['id'] == journey['case'])
        if 'worker interrupted mid-production' not in case['acceptance_oracle']:
            raise SystemExit('Case does not authorize Worker loss qualification')
        interaction = client.request('/api/interactions/'+journey['interaction_id'])
        work_id = interaction.get('governed_work_id')
        if not work_id:
            time.sleep(.5)
            continue
        queue = client.request('/api/native-execution/queue?work_id='+work_id)
        for entry in queue:
            if entry['condition'] != 'EXECUTING':
                continue
            attempt_id = str(UUID(entry['attempt_id']))
            attempt = client.request('/api/native-execution/attempts/'+attempt_id)
            if (not attempt.get('checkpoint') or attempt['state']['effect_uncertainty']
                    or not attempt.get('effects')
                    or any(effect['condition'] not in {'SETTLED','FAILED'} for effect in attempt['effects'])):
                continue
            sql = ("SELECT row_to_json(lease) FROM (SELECT worker_id,epoch,deadline "
                "FROM executor_leases WHERE attempt_id='"+attempt_id+"' AND released_at IS NULL) lease")
            lease_text = subprocess.check_output(['docker','exec',args.project+'-postgres-1',
                'psql','-U','spg','-d','spg_dev','-At','-c',sql],text=True).strip()
            if not lease_text:
                continue
            lease = json.loads(lease_text)
            # Inspect only the declared project's Worker configuration internally;
            # output/evidence never include environment values or credentials.
            workers = subprocess.check_output(['docker', 'ps',
                '--filter', f'label=com.docker.compose.project={args.project}',
                '--filter', 'label=com.docker.compose.service=native-worker',
                '--format', '{{.Names}}'], text=True).splitlines()
            workers += subprocess.check_output(['docker', 'ps',
                '--filter', f'label=com.docker.compose.project={args.project}',
                '--filter', 'label=com.docker.compose.service=native-worker-secondary',
                '--format', '{{.Names}}'], text=True).splitlines()
            selected = []
            for worker in workers:
                details = json.loads(subprocess.check_output(['docker','inspect',worker],text=True))[0]
                values = dict(item.split('=',1) for item in details['Config']['Env'] if '=' in item)
                if values.get('SPG_NATIVE_EXECUTOR_WORKER_ID') == lease['worker_id']:
                    selected.append(worker)
            if len(selected) != 1:
                raise SystemExit('Owning Worker must map to exactly one declared container')
            # Freeze the declared process before checking the crash frontier.
            # A read-then-kill race can otherwise cut a newly dispatched write,
            # contradicting this case's settled-effect fault precondition.
            subprocess.run(['docker','kill','--signal','STOP',selected[0]],
                check=True,capture_output=True)
            frozen = True
            try:
                exact = client.request('/api/native-execution/attempts/'+attempt_id)
                if (exact['state']['worker_epoch'] != lease['epoch']
                        or exact['state']['effect_uncertainty']
                        or any(effect['condition'] not in {'SETTLED','FAILED'}
                               for effect in exact.get('effects', []))
                        or not any(step['kind'] == 'INFERENCE' and step['condition'] == 'RUNNING'
                                   for step in exact.get('steps', []))):
                    continue
                attempt = exact
                record = {'work_id':work_id,'attempt_id':attempt_id,'lease_before':lease,
                    'worker_container':selected[0],'checkpoint_before':attempt['checkpoint'],
                    'settled_effects_before':attempt['effects'],'observed_at':datetime.now(UTC).isoformat(),
                    'fault':'DECLARED_WORKER_PROCESS_LOSS','in_flight_tool_effect':False,
                    'frozen_frontier_verified':True,
                    'database_or_source_mutation':False,'human_work_rescue':False,'human_acceptance':'PENDING'}
                output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
                subprocess.run(['docker','kill','--signal','KILL',selected[0]],
                    check=True,capture_output=True)
                frozen = False
            finally:
                if frozen:
                    subprocess.run(['docker','kill','--signal','CONT',selected[0]],
                        check=True,capture_output=True)
            print(json.dumps({key:record[key] for key in ('work_id','attempt_id','worker_container','fault')}),flush=True)
            return
        time.sleep(.5)
    raise SystemExit('No safe settled checkpoint interruption window observed; do not claim injection')


if __name__ == '__main__':
    main()
