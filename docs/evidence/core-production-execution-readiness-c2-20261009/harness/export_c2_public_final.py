from pathlib import Path
import json,tarfile
ROOT=Path('/data/watt/c2-execution-readiness-20261009');E=ROOT/'evidence'
files=[p for p in E.rglob('*') if p.is_file() and not p.name.endswith('.lock')]
with tarfile.open(str(ROOT/'c2-public-final-20261009.tar'),'w') as archive:
    for path in files:
        assert not path.is_symlink()
        archive.add(str(path),arcname=path.relative_to(E).as_posix(),recursive=False)
print(json.dumps({'public_files':len(files),'private_included':False}))