"""Read-only Git fixture hosting with declared infrastructure fault injection.

Failures affect transport, never project implementation or model output.
Each independent trial should use a fresh server process/fault state.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import os


class Handler(SimpleHTTPRequestHandler):
    failed = False

    def do_GET(self):
        path = urlsplit(self.path).path
        if ('transient-acquisition.git/info/refs' in path and not Handler.failed
                and os.environ.get('GOLDEN_TRANSIENT_ACQUISITION') == 'first-request'):
            Handler.failed = True
            self.send_error(503, 'Declared transient fixture transport outage')
            print('DECLARED_TRANSIENT_ACQUISITION injected once; source unchanged', flush=True)
            return
        super().do_GET()


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
