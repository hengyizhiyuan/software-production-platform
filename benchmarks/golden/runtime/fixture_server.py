"""Read-only Git fixture hosting with declared infrastructure fault injection.

Failures affect transport, never project implementation or model output.
Independent trials use a fresh server process or a unique readonly URL namespace.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlsplit
import os
import re


class Handler(SimpleHTTPRequestHandler):
    failed = 0
    failed_namespaces = {}
    fault_lock = Lock()

    @staticmethod
    def trial_path(path):
        match = re.fullmatch(r'/trials/([A-Za-z0-9_-]{1,100})/(.*)', path)
        return (match[1], '/'+match[2]) if match else (None, path)

    def translate_path(self, path):
        # A declared independent trial URL serves exactly the same readonly Git
        # objects. It separates Product/Asset identity without resetting live
        # Product data, editing source, or giving implementation hints.
        _namespace, translated = self.trial_path(urlsplit(path).path)
        return super().translate_path(translated)

    def do_GET(self):
        path = urlsplit(self.path).path
        namespace, translated = self.trial_path(path)
        budget = int(os.environ.get('GOLDEN_TRANSIENT_ACQUISITION_REQUESTS', '1'))
        fault_number = None
        if ('transient-acquisition.git/info/refs' in translated
                and os.environ.get('GOLDEN_TRANSIENT_ACQUISITION') == 'first-request'):
            with Handler.fault_lock:
                failed = Handler.failed_namespaces.get(namespace, 0) if namespace else Handler.failed
                if failed < budget:
                    fault_number = failed + 1
                    if namespace:
                        Handler.failed_namespaces[namespace] = fault_number
                    else:
                        Handler.failed = fault_number
        if fault_number is not None:
            self.send_error(503, 'Declared transient fixture transport outage')
            print(f'DECLARED_TRANSIENT_ACQUISITION request {fault_number}/{budget}; source unchanged', flush=True)
            return
        super().do_GET()


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
