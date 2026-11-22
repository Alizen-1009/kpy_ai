"""Offline HTTP/SSE fixtures only; these are not service quality evidence."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("probe_service", Path(__file__).resolve().parents[1] / "scripts/vllm_ascend_repro/probe_service.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class Response:
    status = 200

    def __init__(self, body, status=200):
        self.body = io.BytesIO(body)
        self.status = status

    def read1(self, size):
        return self.body.read(1)  # split every UTF-8 codepoint and CRLF

    def read(self, size):
        return self.body.read(size)

    def getheader(self, name, default=""):
        return "text/event-stream; charset=utf-8"


def stream(text="你好", usage=True):
    items = [{"choices": [{"delta": {"content": text}, "index": 0}]},
             {"choices": [{"delta": {}, "finish_reason": "stop"}]}]
    if usage:
        items.append({"choices": [], "usage": {"completion_tokens": 2}})
    return ("".join("data: " + json.dumps(x, ensure_ascii=False) + "\r\n\r\n" for x in items) + "data: [DONE]\n\n").encode()


class ProbeTests(unittest.TestCase):
    def consume(self, body):
        raw = io.StringIO()
        result = probe.consume(Response(body), 0, raw, clock=lambda: 1)
        self.assertIn("raw_event", raw.getvalue())
        return result

    def test_complete(self):
        result = self.consume(stream())
        self.assertEqual(result["text"], "你好")
        self.assertEqual(result["ttft_seconds"], 1)
        self.assertEqual(result["end_to_end_output_tps"], 2)
        self.assertIsNone(result["decode_tps"])

    def test_missing_usage(self):
        self.assertIsNone(self.consume(stream(usage=False))["end_to_end_output_tps"])

    def test_multiline(self):
        body = stream().replace(b'data: {"choices":', b'data: {\ndata: "choices":', 1)
        self.assertEqual(self.consume(body)["text"], "你好")

    def test_fail_closed(self):
        for body in (stream(""), stream()[:-14], b'data: {"error":"oops"}\n\n',
                     b'data: nope\n\n', stream() + b'data: {}\n\n', b'data: \xff\n\n'):
            with self.subTest(body=body), self.assertRaises((ValueError, UnicodeError)):
                self.consume(body)

    def test_url_boundary(self):
        for url in ("http://localhost:80", "http://127.0.0.2:80", "https://127.0.0.1:80",
                    "http://127.0.0.1:80/path", "http://127.0.0.1:0", "http://127.0.0.1:80@evil"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                probe.endpoint(url)
        self.assertEqual(probe.endpoint("http://127.0.0.1:8000"), 8000)

    def test_mock_http(self):
        for mode in ("success", "wrong_model", "network", "http_error"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                calls = []
                class Connection:
                    def __init__(self, host, port, timeout):
                        self.method = None
                        self.closed = False
                        self_test.assertEqual((host, port, timeout), ("127.0.0.1", 8000, 1))
                    def request(self, method, path, *args):
                        calls.append((method, path, args))
                        self.method = method
                        if mode == "network":
                            raise TimeoutError("mock timeout")
                    def getresponse(self):
                        if self.method == "GET":
                            return Response(json.dumps({"data": [{"id": "wrong" if mode == "wrong_model" else "model"}]}).encode())
                        return Response(stream(), 500 if mode == "http_error" else 200)
                    def close(self):
                        self.closed = True
                self_test = self
                args = argparse.Namespace(base_url="http://127.0.0.1:8000", expected_model="model", run_id="unique-fixture", out=str(Path(tmp) / "new"), timeout=1, count=1, max_tokens=64, seed=None)
                self.assertEqual(probe.run(args, Connection), 0 if mode == "success" else 1)
                summary = json.loads((Path(args.out) / "summary.json").read_text())
                self.assertIn("not P2", summary["scope"])
                self.assertEqual(len(calls), 1 if mode in ("wrong_model", "network") else 2)
                if mode == "success":
                    request = json.loads(calls[1][2][0])
                    self.assertTrue(request["stream_options"]["include_usage"])
                    self.assertNotIn("seed", request)
                with self.assertRaises(FileExistsError):
                    probe.run(args, Connection)


if __name__ == "__main__":
    unittest.main()
