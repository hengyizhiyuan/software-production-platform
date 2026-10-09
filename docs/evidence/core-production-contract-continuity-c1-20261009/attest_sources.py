from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import importlib.metadata, json, sys, tarfile
root=Path('/c1')
manifest=json.loads((root/'exact-source-manifest.json').read_text())
folders={'watt':'watt','guardian':'guardian','ecf':'ecf','ecf-unsupported':'ecf-current'}
checks={}
for name, source in manifest['sources'].items():
    archive=root/source['archive']
    assert sha256(archive.read_bytes()).hexdigest()==source['archive_sha256'], name
    total=0
    with tarfile.open(archive) as tf:
        for member in tf:
            if not member.isfile():
                continue
            expected=sha256(tf.extractfile(member).read()).hexdigest()
            actual=sha256((root/folders[name]/member.name).read_bytes()).hexdigest()
            assert actual==expected, (name,member.name)
            total+=1
    checks[name]={'revision':source['revision'],'tree':source['tree'],'archive_sha256':source['archive_sha256'],'verified_file_count':total}
import spg,guardian,ecf,pytest
def package_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return 'UNKNOWN: distribution metadata unavailable'
receipt={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'source_checks':checks,'python':sys.version,'imports':{'spg':spg.__file__,'guardian':guardian.__file__,'ecf':ecf.__file__,'pytest':pytest.__file__},'package_versions':{name:package_version(name) for name in ('pytest','sqlalchemy','psycopg','pydantic','alembic','httpx')}}
(root/'source-attestation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'verified_sources':checks,'python':sys.version.split()[0],'pytest':pytest.__version__}))
