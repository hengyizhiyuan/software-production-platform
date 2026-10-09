# Runs current branch code in memory on the existing ECS API image. No remote
# files are written, no production credentials are printed or copied locally.
# Requires the operator's already configured watt-ecs SSH alias.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$traceSource = Get-Content (Join-Path $root 'src/spg/evaluation/production_trace.py') -Raw -Encoding UTF8
$exportSource = Get-Content (Join-Path $root 'src/spg/evaluation/work_diagnostic_export.py') -Raw -Encoding UTF8
$traceB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($traceSource))
$exportB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($exportSource))
$bootstrap = @'
import base64, json, time
from uuid import UUID
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from hashlib import sha256
from sqlalchemy import event, text
from spg.config import Settings
from spg.infrastructure.persistence import Database
from spg.evaluation.service import QualityService
from spg.evaluation import production_trace

trace_scope = {'__name__':'spg.evaluation.production_trace', '__package__':'spg.evaluation'}
exec(compile(base64.b64decode('TRACE_B64'), 'production_trace.py', 'exec'), trace_scope)
production_trace.ProductionTraceService.entity_trace = trace_scope['ProductionTraceService'].entity_trace
production_trace.ProductionTraceService._work_tables = trace_scope['ProductionTraceService']._work_tables
export_scope = {'__name__':'spg.evaluation.work_diagnostic_export', '__package__':'spg.evaluation'}
exec(compile(base64.b64decode('EXPORT_B64'), 'work_diagnostic_export.py', 'exec'), export_scope)
settings = Settings()
database = Database.from_settings(settings)
@event.listens_for(database.engine, 'connect')
def readonly(dbapi_connection, connection_record):
    previous = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    try:
        with dbapi_connection.cursor() as cursor:
            cursor.execute('SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY')
    finally:
        dbapi_connection.autocommit = previous
exporter = export_scope['WorkDiagnosticExportService'](database, settings, QualityService(database, settings))
for label, wid, mode in [('design','408e408a-fab8-5a34-b101-b922043cb6fd','compact'), ('production','3ee622b5-b816-5679-afdc-e5de51cd2702','full')]:
    started = time.monotonic()
    with database.engine.connect() as connection:
        owner = connection.scalar(text('select p.owner_id from product_works w join software_products p on p.id=w.product_id where w.id=:wid'), {'wid':UUID(wid)})
        read_only = connection.scalar(text('show transaction_read_only'))
    assert owner and read_only == 'on', 'READ_ONLY_OWNER_NOT_PROVEN'
    files = exporter.capture(owner, UUID(wid), mode=mode)
    manifest = json.loads(files['evidence-manifest.json'])
    trace = json.loads(files['trace.json'])['lifecycle']
    for filename, value in manifest['exported_files'].items():
        assert sha256(files[filename]).hexdigest() == value['sha256']
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for filename, value in files.items():
            archive.writestr(filename, value)
    with ZipFile(BytesIO(output.getvalue())) as archive:
        assert set(archive.namelist()) == set(files)
    if label == 'design':
        assert (trace.get('work') or {}).get('stage') == 'DESIGN'
        assert not trace['units'] and not trace['candidate'] and len(trace['conversation']) >= 1
    else:
        assert trace['units'] and trace['candidate'] and trace['recovery'] and trace['verification'] and trace['guardian']
    print(json.dumps({'case':label,'work_id':wid,'mode':mode,'db_read_only':read_only,
        'work_state':(trace.get('work') or {}).get('state'),
        'work_stage':(trace.get('work') or {}).get('stage'),
        'units':len(trace.get('units') or []),'candidate':len(trace.get('candidate') or []),
        'conversation':len(trace.get('conversation') or []),
        'steering_decisions':sum(e.get('source_ref','').startswith('steering_decisions:') for e in trace.get('timeline') or []),
        'recovery':len(trace.get('recovery') or []),'verification':len(trace.get('verification') or []),
        'guardian':len(trace.get('guardian') or []),'zip_bytes':len(output.getvalue()),
        'total_uncompressed_bytes':sum(map(len,files.values())),'truncated':bool(manifest.get('truncated_records')),
        'hash_verified':True,'elapsed_seconds':round(time.monotonic()-started,3)},sort_keys=True))
database.dispose()
'@
$bootstrap = $bootstrap.Replace('TRACE_B64', $traceB64).Replace('EXPORT_B64', $exportB64)
$bootstrap | ssh -T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=8 watt-ecs "docker exec -i -e PYTHONDONTWRITEBYTECODE=1 watt-cloud-worker-api-1 python -"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
