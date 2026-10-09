from pathlib import Path
import datetime, json, subprocess
root = Path('/data/watt/c1-contract-qualification-20261009')
expected = [
 ('31dd06710bb26fd540f25256f73cd0a8905b6f305fd1b8bd6b48d4a27b9c0633', '/watt-c1-contract-runner-20261009'),
 ('cf39d07e1b6ac9edc9c14db58be3b101e746f286bdf1f53a820602d0b23ee053', '/watt-c1-postgres-20261009'),
]
def output(args):
    return subprocess.check_output(args, universal_newlines=True).strip()
def running():
    return sorted(output(['docker','ps','--no-trunc','--format','{{.ID}}']).splitlines())
def production():
    return {'head': output(['git','-C','/data/watt/runtime/source','rev-parse','HEAD']), 'dirty': output(['git','-C','/data/watt/runtime/source','status','--porcelain'])}
before = running()
pbefore = production()
assert pbefore == {'head':'ee5bd86a53891f9391785c91d0ccef81ad2d56c3', 'dirty':''}, pbefore
checked = []
for identifier, name in expected:
    data = json.loads(output(['docker','inspect',identifier]))[0]
    assert data['Id'] == identifier and data['Name'] == name
    assert data['Config']['Labels'] == {'watt.production':'false', 'watt.qualification':'C1-contract-continuity'}
    assert not data['HostConfig']['PortBindings']
    if 'runner' in name:
        assert data['HostConfig']['NetworkMode'] == 'container:' + expected[1][0]
        assert len(data['Mounts']) == 1 and data['Mounts'][0]['Source'] == str(root) and data['Mounts'][0]['Destination'] == '/c1'
    else:
        assert data['HostConfig']['NetworkMode'] == 'none' and data['Mounts'] == []
    checked.append({'id':identifier,'name':name,'labels_verified':True,'isolated_mounts_verified':True})
removed = []
for identifier, name in expected:
    # Revalidate immediately before stopping this exact newly-created container.
    data = json.loads(output(['docker','inspect',identifier]))[0]
    assert data['Id'] == identifier and data['Name'] == name and data['Config']['Labels']['watt.qualification'] == 'C1-contract-continuity'
    subprocess.check_call(['docker','stop','--time','10',identifier], stdout=subprocess.DEVNULL)
    subprocess.check_call(['docker','rm',identifier], stdout=subprocess.DEVNULL)
    removed.append(identifier)
after = running()
pafter = production()
assert after == sorted(set(before) - set(removed)), {'before':before,'after':after}
assert pafter == pbefore
receipt = {'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'checked':checked, 'removed_exact_ids':removed, 'existing_running_ids_before':sorted(set(before)-set(removed)), 'existing_running_ids_after':after, 'existing_running_id_set_unchanged':True, 'production_source_before':pbefore, 'production_source_after':pafter, 'persistent_evidence_root_retained':str(root), 'fixture_tmpfs_database_discarded':True, 'images_volumes_credentials_untouched':True}
(root/'cleanup-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'removed_exact_ids':removed,'existing_running_id_set_unchanged':True,'production_source':pafter,'receipt':str(root/'cleanup-receipt.json')}))
