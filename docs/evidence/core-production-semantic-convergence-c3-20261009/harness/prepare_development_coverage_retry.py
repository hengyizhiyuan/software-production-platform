from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import ast,copy,json,tarfile
W=Path(r'C:\Users\yuchunbo\.codex\worktrees\c3-open-obligation-convergence\software-production-platform')
E=W/'docs/evidence/core-production-semantic-convergence-c3-20261009'
NAME='dev-regression-3-coverage-integration'
D=W/'.c3-development-inputs'/NAME; assert not D.exists();D.mkdir()
M=json.loads((E/'dev-regression-3-guardian-contract/development-inputs.json').read_text(encoding='utf-8'))
M=copy.deepcopy(M);M['directory']=NAME;M['captured_at_utc']=datetime.now(timezone.utc).isoformat()
M['scope']='Targeted coverage aggregation correction; exact Snapshot3+formal fixture override+three-file repair; no live model or AI Work'
paths=('src/spg/application/verification.py','src/spg/application/guardian_assurance.py','tests/test_c3_evidence_projection.py')
archive=D/'watt-coverage-repair.tar';digests={}
with tarfile.open(archive,'w') as out:
    for relative in paths:
        raw=(W/relative).read_bytes();ast.parse(raw.decode('utf-8'),filename=relative)
        digests[relative]=sha256(raw).hexdigest();out.add(W/relative,arcname=relative,recursive=False)
M['coverage_repair']={'archive':archive.name,'sha256':sha256(archive.read_bytes()).hexdigest(),'file_sha256':digests,'ast_result':'PASS','content_scope':'two source files + corresponding focused regression tests only'}
effective=dict(M['watt']['file_sha256']);effective.update(M['fixture_patch']['file_sha256']);effective.update(digests)
M['sources']['watt']['python_paths_sha256']=sha256(''.join(p+' '+effective[p]+'\n' for p in sorted(effective) if p.endswith('.py')).encode()).hexdigest()
M['effective_watt_file_sha256']=effective
M['groups']=[{'name':'watt-coverage','nodes':['tests/test_c3_evidence_projection.py']},{'name':'c1-positive','nodes':['tests/integration/test_c1_contract_continuity.py::test_both_actual_admission_paths_reach_independent_guardian']}]
M['prior_failure']={'source_directory':'dev-regression-3-guardian-contract','c1_counts':{'passed':0,'failures':2,'errors':0,'skipped':0},'actual_guardian_finding':'six CONTEXT_COVERAGE_GAP per exact candidate; related verification refs empty','owner_records':'last-c1-full-owner-records.json','exact_cause':'PATH_SCOPE six actual protected checks covered; GIT_DIFF_CHECK zero protected checks with generated UNVERIFIED placeholders caused Adapter ambiguous aggregation','correction':'only exact identified unconsumed checks marked NOT_EVALUATED_BY_THIS_CHECK; relevant UNVERIFIED, wrong identity and conflict still reject'}
M['harness_sha256']=sha256((E/'harness/run_final_image_regression.py').read_bytes()).hexdigest()
(D/'development-inputs.json').write_text(json.dumps(M,indent=2)+'\n',encoding='utf-8')
P=E/NAME;assert not P.exists();P.mkdir();(P/'development-inputs.json').write_text(json.dumps(M,indent=2)+'\n',encoding='utf-8')
s=(E/'harness/run_development_regression_3_guardian_contract.py').read_text(encoding='utf-8')
s=s.replace('development-inputs-dev-regression-3-guardian-contract.json','development-inputs-'+NAME+'.json')
s=s.replace('assert manifest["directory"]=="dev-regression-3-guardian-contract"','assert manifest["directory"]=="'+NAME+'"')
start=s.index('guardian=ROOT/');end=s.index('for relative,digest in manifest["guardian"]["file_sha256"].items():',start)
s=s[:start]+'''guardian=ROOT/"dev-regression-3-guardian-contract-input";assert guardian.is_dir()
garchive=ROOT/manifest["guardian"]["archive"];assert sha256(garchive.read_bytes()).hexdigest()==manifest["guardian"]["sha256"]
'''+s[end:]
pos=s.index('IMAGE=')
s=s[:pos]+'''repair=ROOT/"dev-regression-3-coverage-input";assert not repair.exists();repair.mkdir()
rarchive=ROOT/manifest["coverage_repair"]["archive"]
assert sha256(rarchive.read_bytes()).hexdigest()==manifest["coverage_repair"]["sha256"]
with tarfile.open(str(rarchive)) as inputs:
    for member in inputs.getmembers():
        relative=Path(member.name);assert not relative.is_absolute() and ".." not in relative.parts
        assert member.isfile();inputs.extract(member,str(repair))
for relative,digest in manifest["coverage_repair"]["file_sha256"].items():
    assert sha256((repair/relative).read_bytes()).hexdigest()==digest
'''+s[pos:]
s=s.replace('name="watt-c3-dev3-contract-"+group["name"]+"-20261009"','name="watt-c3-dev3-coverage-"+group["name"]+"-20261009"')
needle='    started=datetime.now(timezone.utc).isoformat();start=time.monotonic();raw=P/(name+".raw.log")'
addition='''    for relative in manifest["coverage_repair"]["file_sha256"]:
        position=args.index("--workdir")
        args[position:position]=["--mount","type=bind,src="+str(repair/relative)+",dst=/qualification/"+relative+",readonly"]
'''
s=s.replace(needle,addition+needle)
# Avoid two file bind mounts targeting the same tests path: latest repair replaces that one fixture override.
s=s.replace('for relative in manifest["fixture_patch"]["file_sha256"]:\n        position=', 'for relative in manifest["fixture_patch"]["file_sha256"]:\n        if relative in manifest["coverage_repair"]["file_sha256"]:continue\n        position=')
s=s.replace('"database_name":"c1_contract_continuity","database_configuration_key":"SPG_TEST_DATABASE_URL"}', '"database_name":"c1_contract_continuity","database_configuration_key":"SPG_TEST_DATABASE_URL","harness_sha256":sha256(Path(__file__).read_bytes()).hexdigest()}')
runner=E/'harness/run_development_coverage_retry.py';assert not runner.exists();runner.write_text(s,encoding='utf-8');ast.parse(s)
M['execution_harness_sha256']=sha256(runner.read_bytes()).hexdigest()
for destination in (D/'development-inputs.json',P/'development-inputs.json'):destination.write_text(json.dumps(M,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'directory':NAME,'source_digest':M['sources']['watt']['python_paths_sha256'],'repair':M['coverage_repair'],'runner_sha256':M['execution_harness_sha256']}))