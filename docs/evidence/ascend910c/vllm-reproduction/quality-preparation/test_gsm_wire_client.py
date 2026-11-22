import base64
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.request
from gsm_wire_client import Capture

ROOT = Path(__file__).parent

class WireTests(unittest.TestCase):
    def capture(self, wire, streaming=False):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            request = urllib.request.Request('http://127.0.0.1:1/v1/completions', data=b'{"prompt":"unchanged"}')
            with Capture(io.BytesIO(wire), request, directory) as response:
                actual = b''.join(response) if streaming else response.read()
            records = list(Path(directory).glob('*.json'))
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text())
            self.assertEqual(actual, wire)
            self.assertEqual(base64.b64decode(record['response_body_base64']), wire)
            self.assertEqual(base64.b64decode(record['request_body_base64']), request.data)
            return record

    def test_json_usage_finish(self):
        self.capture(b'{"choices":[{"text":"42","finish_reason":"stop"}],"usage":{"prompt_tokens":17}}')

    def test_sse_usage_finish(self):
        self.capture(b'data: {"choices":[{"text":"42","finish_reason":"length"}]}\n\ndata: {"choices":[],"usage":{"prompt_tokens":17}}\n\ndata: [DONE]\n\n', True)

    def test_malformed_not_fabricated(self):
        record = self.capture(b'not json\xff', True)
        self.assertNotIn('usage', record)
        self.assertNotIn('passed', record)

    def test_empty_not_fabricated(self):
        record = self.capture(b'')
        self.assertEqual(record['response_body_base64'], '')
        self.assertNotIn('finish_reason', record)

if __name__ == '__main__':
    unittest.main()
