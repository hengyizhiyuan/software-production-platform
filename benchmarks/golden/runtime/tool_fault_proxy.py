"""Declared, once-only no-effect infrastructure fault before a real read.

Runs outside Watt. It forwards every other request unchanged to the real Tool
Host. It never alters source, grants, model output or successful effect receipts.
The failed delivery remains queryable so restart recovery cannot replay it as an
uncertain side effect. Console evidence contains identities, never credentials.
"""
from hashlib import sha256
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Lock
from uuid import UUID
import urllib.error
import urllib.request


class Handler(BaseHTTPRequestHandler):
    lock = Lock()
    fault = None
    upstream = os.environ.get('GOLDEN_TOOL_HOST_UPSTREAM', 'http://native-tool-host:8011')
    internal_token = os.environ.get('SPG_NATIVE_EXECUTOR_INTERNAL_TOKEN', '')
    targeted = os.environ.get('GOLDEN_FAULT_MODE') == 'targeted'
    targets = {}
    injected_work = set()
    retained_path = os.environ.get('GOLDEN_FAULT_RECEIPTS_PATH')
    receipts = {} if not retained_path else json.loads(Path(retained_path).read_text())

    def log_message(self, *_):
        pass

    def reply(self, value, status=200, content_type='application/json'):
        body = value if isinstance(value, bytes) else json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        for identity, receipt in Handler.receipts.items():
            if self.path.endswith('/'+identity+'/receipt'):
                return self.reply(receipt)
        if Handler.fault is not None and self.path.endswith(
                '/'+Handler.fault['delivery_id']+'/receipt'):
            return self.reply(Handler.fault)
        self.forward()

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if self.path == '/qualification/no-effect-file-read':
            if (not Handler.targeted or not Handler.internal_token or not hmac.compare_digest(
                    self.headers.get('X-Watt-Internal-Token',''),Handler.internal_token)):
                return self.reply({'error':'qualification declaration unavailable'},403)
            declaration = json.loads(body)
            work_id = str(UUID(declaration['work_id']))
            evidence_id = declaration['evidence_id']
            if not evidence_id.startswith('GC-EX-05:trial-'):
                return self.reply({'error':'case does not authorize this fault'},400)
            with Handler.lock:
                if work_id in Handler.targets:
                    return self.reply({'error':'declaration identity is immutable'},409)
                Handler.targets[work_id] = evidence_id
            return self.reply({'work_id':work_id,'evidence_id':evidence_id,
                'declared':True,'source_modified':False,'effect_injected':False})
        if self.path == '/internal/native-tools/execute':
            request = json.loads(body)
            proposal = request['proposal']
            # Qualification probes and baseline context reads remain unaffected.
            eligible = (bool(Handler.internal_token)
                and hmac.compare_digest(self.headers.get('X-Watt-Internal-Token', ''), Handler.internal_token)
                and proposal['tool_identity'] == 'file.read'
                and proposal['arguments'].get('path') not in {'README.md', 'AI_context.md'})
            with Handler.lock:
                work_id = str(request['workspace']['work_id'])
                selected = (work_id in Handler.targets and work_id not in Handler.injected_work
                    if Handler.targeted else Handler.fault is None)
                if eligible and selected:
                    output = {'error_type': 'CAPABILITY_PATH_INVALID',
                        'message': 'Declared primary read recipe unavailable before execution; use an admitted alternative',
                        'effect_observed': False}
                    digest = sha256(json.dumps(output, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=False).encode()).hexdigest()
                    Handler.fault = {'delivery_id': request['delivery_id'],
                        'tool_identity': 'file.read', 'condition': 'FAILED',
                        'output': output, 'output_digest': digest,
                        'evidence': [{'kind': 'DECLARED_NO_EFFECT_TRANSPORT_FAULT',
                            'forwarded_to_tool_host': False}]}
                    Handler.injected_work.add(work_id)
                    Handler.receipts[request['delivery_id']] = Handler.fault
                    print(json.dumps({'fault': Handler.fault,
                        'attempt_id': request['attempt_id'],
                        'work_id': request['workspace']['work_id']}), flush=True)
                    return self.reply(Handler.fault)
        self.forward(body)

    def forward(self, body=None):
        request = urllib.request.Request(Handler.upstream+self.path, data=body,
            method=self.command, headers={
                'Content-Type': self.headers.get('Content-Type', 'application/json'),
                'X-Watt-Internal-Token': self.headers.get('X-Watt-Internal-Token', '')})
        try:
            with urllib.request.urlopen(request, timeout=240) as response:
                self.reply(response.read(), response.status, response.headers.get('Content-Type'))
        except urllib.error.HTTPError as error:
            self.reply(error.read(), error.code, error.headers.get('Content-Type'))


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8012), Handler).serve_forever()
