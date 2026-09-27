"""Read-only Git fixture hosting with declared infrastructure fault injection.

Failures affect transport, never project implementation or model output.
Independent trials use a fresh server process or a unique readonly URL namespace.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import os
import re


class Handler(SimpleHTTPRequestHandler):
    failed = False
    failed_namespaces = set()

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
        failed = namespace in Handler.failed_namespaces if namespace else Handler.failed
        if ('transient-acquisition.git/info/refs' in translated and not failed
                and os.environ.get('GOLDEN_TRANSIENT_ACQUISITION') == 'first-request'):
            if namespace:
                Handler.failed_namespaces.add(namespace)
            else:
                Handler.failed = True
            self.send_error(503, 'Declared transient fixture transport outage')
            print('DECLARED_TRANSIENT_ACQUISITION injected once; source unchanged', flush=True)
            return
        super().do_GET()


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
