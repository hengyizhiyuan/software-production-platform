"""Declared source-overlay development regression; never an exact-image claim."""
import argparse
from datetime import datetime
from hashlib import sha256
import json, os, subprocess, tarfile, time
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path('/data/watt/c3-semantic-convergence-20261009/capacity-representation-20261009')
IMAGE='sha256:4d3c64b1e3543a3574cd69b435d6f703fad6edc23b9db7d54d799dc1a652bf6e'

def prepare(args):
    target=Path('.c3-development-inputs')/('capacity-dev-'+args.name)
    assert not target.exists()
    target.mkdir()
    with tarfile.open(str(target/'snapshot.tar'),'w') as archive:
        for directory in ('src','tests'):
            for file in Path(directory).rglob('*'):
                if file.is_file() and '__pycache__' not in file.parts:
                    archive.add(str(file),arcname=file.as_posix(),recursive=False)
    manifest={'sha256':sha256((target/'snapshot.tar').read_bytes()).hexdigest(),
        'captured_at_utc':datetime.utcnow().isoformat()+'Z','name':args.name,'nodes':args.nodes,
        'source_overlay':True,'purpose':'Development only; no model calls, business Work, or final source qualification'}
    (target/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'prepared_directory':str(target),'manifest':manifest}))

def execute(args):
    inputs=Path(args.inputs)
    manifest=json.loads((inputs/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['name']==args.name
    assert manifest['sha256']==sha256((inputs/'snapshot.tar').read_bytes()).hexdigest()
    target=ROOT/('development-'+args.name)
    assert not target.exists()
    target.mkdir()
    with tarfile.open(str(inputs/'snapshot.tar')) as archive:
        members=archive.getmembers()
        for member in members:
            path=Path(member.name)
            assert not path.is_absolute() and '..' not in path.parts and member.isfile()
            file=target/'snapshot'/path
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(archive.extractfile(member).read())
    evidence=target/'evidence';evidence.mkdir();os.chown(str(evidence),10001,10001)
    pytest=['python','-m','pytest','-p','no:cacheprovider','-o','junit_family=legacy']+manifest['nodes']+['--tb=short','--junitxml=/c3-evidence/result.xml']
    cmd=['docker','create','--network','none','--read-only','--user','10001:10001','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--memory','1536m','--cpus','1','--tmpfs','/tmp:rw,exec,nosuid,size=512m',
        '--workdir','/c3-development','-e','PYTHONPATH=/c3-development/src:/opt/c3-owners/guardian/src:/opt/c3-owners/ecf/src:/opt/c3-test-deps',
        '-v',str(target/'snapshot')+':/c3-development:ro','-v',str(evidence)+':/c3-evidence:rw',IMAGE]+pytest
    cid=subprocess.check_output(cmd,universal_newlines=True).strip()
    started=datetime.utcnow().isoformat()+'Z';clock=time.monotonic()
    with (evidence/'result.log').open('x') as stream:
        subprocess.run(['docker','start','-a',cid],stdout=stream,stderr=subprocess.STDOUT)
    actual=json.loads(subprocess.check_output(['docker','inspect',cid],universal_newlines=True))[0]
    counts={k:0 for k in ('tests','failures','errors','skipped')}
    if (evidence/'result.xml').exists():
        for suite in ET.parse(str(evidence/'result.xml')).iter('testsuite'):
            for key in counts:counts[key]+=int(suite.get(key,'0'))
    counts['passed']=counts['tests']-sum(counts[k] for k in ('failures','errors','skipped'))
    receipt={'manifest':manifest,'actual_image':actual['Image'],'actual_container_id':cid,
        'started_at_utc':started,'ended_at_utc':datetime.utcnow().isoformat()+'Z','wall_seconds':time.monotonic()-clock,
        'exit_code':actual['State']['ExitCode'],'counts':counts,'source_overlay':True,'network_mode':actual['HostConfig']['NetworkMode'],
        'model_calls':0,'source_file_sha256':{f.relative_to(target/'snapshot').as_posix():sha256(f.read_bytes()).hexdigest()
            for f in (target/'snapshot').rglob('*') if f.is_file()},'controller_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    (evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'counts':counts,'exit_code':receipt['exit_code'],'wall_seconds':receipt['wall_seconds'],'source_overlay':True}))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--execute',action='store_true')
    parser.add_argument('--name',required=True);parser.add_argument('--inputs');parser.add_argument('nodes',nargs='*')
    args=parser.parse_args()
    assert args.prepare!=args.execute
    if args.prepare:prepare(args)
    else:execute(args)
