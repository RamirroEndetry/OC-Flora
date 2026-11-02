# -*- coding: utf-8 -*-
"""Lokální statický server s podporou HTTP Range (nutné pro přehrávání videa spořiče v prohlížeči).
Usage: python scripts/serve.py [port]   (výchozí 5180, kořen = složka projektu)
"""
import os, re, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5180


class RangeHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def send_head(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or os.path.isdir(path) or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r'bytes=(\d*)-(\d*)$', rng.strip())
        size = os.path.getsize(path)
        if not m:
            return super().send_head()
        start = int(m.group(1)) if m.group(1) else max(0, size - int(m.group(2) or 0))
        end = int(m.group(2)) if m.group(1) and m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return None
        f = open(path, 'rb')
        f.seek(start)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length', str(end - start + 1))
        self.end_headers()
        self._range_len = end - start + 1
        return f

    def copyfile(self, source, outputfile):
        n = getattr(self, '_range_len', None)
        if n is None:
            return super().copyfile(source, outputfile)
        self._range_len = None
        while n > 0:
            chunk = source.read(min(65536, n))
            if not chunk:
                break
            outputfile.write(chunk)
            n -= len(chunk)

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))


if __name__ == '__main__':
    print(f'OC Flora app: http://localhost:{PORT}/  (root {ROOT})', flush=True)
    ThreadingHTTPServer(('127.0.0.1', PORT), RangeHandler).serve_forever()
