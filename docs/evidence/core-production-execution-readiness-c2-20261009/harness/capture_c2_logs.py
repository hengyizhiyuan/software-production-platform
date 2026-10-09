from pathlib import Path
from datetime import datetime,timezone
import base64,json,os,re,subprocess
ROOT=Path('/data/watt/c2-execution-readiness-20261009');P=ROOT/'private';E=ROOT/'evidence'
secrets=[]
for path in P.glob('*.env'):
    for line in path.read_text().splitlines():
        if '=' not in line:continue
        key,value=line.split('=',1)
        if value and any(word in key for word in ('KEY','TOKEN','PASSWORD','DATABASE_URL')):secrets.append(value)
credentials=json.loads((P/'credentials.json').read_text());secrets += [str(value) for key,value in credentials.items() if any(word in key for word in ('password','token'))]
secrets.append(base64.b64encode((credentials['gitea_user']+':'+credentials['gitea_password']).encode()).decode())
for role in ('api','worker','tool-host','coordinator'):
    name='watt-c2-'+role+'-20261009'
    data=json.loads(subprocess.check_output(['docker','inspect',name],universal_newlines=True))[0]
    assert data['Config']['Labels'].get('watt.qualification')=='C2-execution-readiness' and data['Image']=='sha256:205f7b42539767939675cebd6e8380be2757c5ebd6d7fbb08828bffae7799209'
    result=subprocess.run(['docker','logs',name],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True)
    raw=P/(name+'.runtime.raw.log')
    with raw.open('w') as stream:os.fchmod(stream.fileno(),0o600);stream.write(result.stdout)
    safe=result.stdout
    for value in sorted(set(secrets),key=len,reverse=True):safe=safe.replace(value,'[REDACTED]')
    (E/(name+'.runtime.log')).write_text(safe)
    selected=[line for line in safe.splitlines() if any(word in line for word in ('ERROR','Traceback','Error:','FAIL','timeout','Unable'))]
    print(json.dumps({'role':role,'state':data['State']['Status'],'diagnostic_error_lines':selected[-15:],'captured_at_utc':datetime.now(timezone.utc).isoformat()}),flush=True)