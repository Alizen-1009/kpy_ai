#!/usr/bin/env python3
"""Run frozen GSM client unchanged, retaining exact response bytes in sidecars.
Set GSM_WIRE_DIR to a new directory. No model requests occur on import.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import runpy
import threading
import urllib.request
import uuid


class Capture:
    def __init__(self, response, request, directory):
        self.response = response
        self.request = request
        self.directory = Path(directory)
        self.parts = []
        self.saved = False
        self.error = None

    def read(self, *args):
        try:
            data = self.response.read(*args)
            self.parts.append(data)
            return data
        except Exception as exc:
            self.error = repr(exc)
            raise

    def __iter__(self):
        try:
            for raw in self.response:
                self.parts.append(raw)
                yield raw
        except Exception as exc:
            self.error = repr(exc)
            raise

    def close(self):
        try:
            self.response.close()
        finally:
            if not self.saved:
                self.saved = True
                payload = self.request.data or b''
                wire = b''.join(self.parts)
                record = {'url': self.request.full_url,
                          'request_body_base64': base64.b64encode(payload).decode(),
                          'request_sha256': hashlib.sha256(payload).hexdigest(),
                          'response_body_base64': base64.b64encode(wire).decode(),
                          'response_sha256': hashlib.sha256(wire).hexdigest(),
                          'status': getattr(self.response, 'status', None),
                          'error': self.error,
                          'note': 'Raw bytes retain usage/finish_reason; not a quality verdict.'}
                path = self.directory / (uuid.uuid4().hex + '.json')
                with path.open('x') as output:
                    json.dump(record, output, ensure_ascii=False, indent=2)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def main():
    directory = Path(os.environ['GSM_WIRE_DIR']).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    original = urllib.request.urlopen
    def captured(request, *args, **kwargs):
        return Capture(original(request, *args, **kwargs), request, directory)
    urllib.request.urlopen = captured
    try:
        runpy.run_path(str(Path(__file__).parent / 'reference/tests/acc_eval.py'), run_name='__main__')
    finally:
        urllib.request.urlopen = original


if __name__ == '__main__':
    main()
