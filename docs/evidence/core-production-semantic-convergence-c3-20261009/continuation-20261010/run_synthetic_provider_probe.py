"""One synthetic diagnostic, one exact retained image, provider-only credentials."""
import argparse,json,os,subprocess
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
ROOT=Path('/data/watt/c3-semantic-convergence-20261009');TARGET=ROOT/'continuation-20261010/synthetic-provider-probe-1'
IMAGE='sha256:51c0b8be88969720cb3a3cfc4e047edc7f229aa22348a95a89cbb4bf83a18e39';NAME='watt-c3-synthetic-provider-probe1-20261009'
def main():
 assert not TARGET.exists()
 for p in (ROOT,)+tuple(ROOT.parents):assert not p.is_symlink()
 TARGET.parent.mkdir(mode=0o750,exist_ok=True);assert not TARGET.parent.is_symlink();TARGET.mkdir(mode=0o750)
 private=TARGET/'private';private.mkdir(mode=0o700);evidence=TARGET/'evidence';evidence.mkdir(mode=0o750);os.chown(str(evidence),10001,10001)
 source=ROOT/'retry-1/private/watt-c3-retry1-api-20261009.env';assert source.is_file() and not source.is_symlink() and source.stat().st_mode&0o077==0
 allowed={'SPG_DEEPSEEK_API_KEY','SPG_DEEPSEEK_BASE_URL','SPG_WIC_PROVIDER_ADAPTER','SPG_WIC_PROVIDER_MODEL','SPG_WIC_PROVIDER_REASONING_EFFORT','SPG_COLLABORATION_PROVIDER_TIMEOUT_SECONDS','SPG_COLLABORATION_PROVIDER_MAX_OUTPUT_TOKENS'}
 settings={k:v for k,v in (line.split('=',1) for line in source.read_text().splitlines() if '=' in line) if k in allowed};assert settings.get('SPG_DEEPSEEK_API_KEY') and settings.get('SPG_DEEPSEEK_BASE_URL')=='https://api.deepseek.com'
 env=private/'provider-only.env'
 with env.open('x') as f:
  os.fchmod(f.fileno(),0o600)
  for k,v in settings.items():f.write(k+'='+v+'\n')
 assert subprocess.check_output(['docker','image','inspect','--format','{{.Id}}',IMAGE],universal_newlines=True).strip()==IMAGE
 assert subprocess.run(['docker','inspect',NAME],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
 script=ROOT/'p0_synthetic_probe.py';assert script.is_file() and not script.is_symlink()
 command=['docker','run','--name',NAME,'--network','watt-c3-control-20261009','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--read-only','--tmpfs','/tmp:rw,nosuid,size=256m','--memory','1536m','--cpus','1','--pids-limit','128','--label','watt.production=false','--label','watt.qualification=C3-synthetic-provider-diagnostic','--env-file',str(env),'--mount','type=bind,src='+str(script)+',dst=/probe.py,readonly','--mount','type=bind,src='+str(evidence)+',dst=/c3-evidence',IMAGE,'python','/probe.py']
 with (private/'probe.raw.log').open('x') as stream:
  os.fchmod(stream.fileno(),0o600);result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT)
 actual=json.loads(subprocess.check_output(['docker','inspect',NAME],universal_newlines=True))[0];assert actual['Image']==IMAGE
 receipt={'schema':'c3-synthetic-provider-container-v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'exit_code':result.returncode,'actual_container_id':actual['Id'],'actual_image_id':actual['Image'],'user':actual['Config']['User'],'mounts':actual['Mounts'],'source_revision':actual['Config']['Labels'].get('org.opencontainers.image.revision'),'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),'probe_sha256':sha256(script.read_bytes()).hexdigest(),'historical_data_mounted_or_sent':False,'business_database_access':False,'new_work_created':False,'existing_services_started':False}
 (evidence/'container-identity.json').write_text(json.dumps(receipt,indent=2)+'\n')
 report=evidence/'provider-probe.json'
 if report.is_file():
  d=json.loads(report.read_text());print(json.dumps({k:d.get(k) for k in ('result','exception_type','failure_boundary','profile','http_observations','provider_failure','numeric_usage','wall_seconds')}))
 else:print(json.dumps({'receipt':'NOT_CAPTURED','exit_code':result.returncode}))
 assert result.returncode==0 and report.is_file()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
 if args.execute:main()
 else:print(json.dumps({'plan':True,'historical_data':False,'work_created':False,'model_calls':0}))