import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import importlib.util

spec = importlib.util.spec_from_file_location('download_assets', Path(__file__).with_name('download_assets.py'))
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class Response(io.BytesIO):
    def getcode(self):
        return 200


class Opener:
    def __init__(self, data=b'abc', interrupt=False):
        self.data, self.interrupt, self.calls = data, interrupt, 0

    def open(self, url, timeout):
        self.calls += 1
        if self.interrupt:
            class Interrupted(Response):
                def read(self, n):
                    raise KeyboardInterrupt
            return Interrupted(self.data)
        return Response(self.data)


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = d.destination(self.base / 'assets', True)
        self.row = {'Path': 'sub/a', 'Size': 3, 'Sha256': hashlib.sha256(b'abc').hexdigest()}
        self.space = patch.object(d.os, 'statvfs', return_value=SimpleNamespace(f_bavail=10**15, f_frsize=1))
        self.space.start()
        self.addCleanup(self.space.stop)

    def run_download(self, opener=None):
        d.run([self.row], self.root, True, opener=opener or Opener())

    def test_success_and_verified_skip(self):
        self.run_download()
        opener = Opener()
        self.run_download(opener)
        self.assertEqual(opener.calls, 0)
        self.assertEqual((self.root / 'sub/a').read_bytes(), b'abc')
        self.assertFalse((self.root / 'sub/a.part').exists())

    def test_existing_mismatch(self):
        (self.root / 'sub').mkdir()
        (self.root / 'sub/a').write_bytes(b'bad')
        with self.assertRaises(ValueError):
            self.run_download()
        self.assertEqual((self.root / 'sub/a').read_bytes(), b'bad')

    def test_invalid_inventory(self):
        cases = [{'Path': p} for p in ('/a', '../a', 'a/../b', 'a//b', './a', 'a\\b', d.MARKER)]
        cases += [{'Size': x} for x in (-1, True, '3', 1.5)]
        cases += [{'Sha256': x} for x in ('x'*64, '', None)]
        for change in cases:
            with self.subTest(change=change):
                manifest = self.base / 'manifest.json'
                manifest.write_text(json.dumps([dict(self.row, **change)]))
                with self.assertRaises(ValueError):
                    d.inventory(manifest)
        manifest.write_text(json.dumps([self.row, self.row]))
        with self.assertRaises(ValueError):
            d.inventory(manifest)

    def test_symlink_ancestor(self):
        (self.root / 'sub').symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.run_download()

    def test_marker_and_dry_run(self):
        other = self.base / 'other'
        other.mkdir()
        (other / 'foreign').touch()
        with self.assertRaises(ValueError):
            d.destination(other, True)
        dry = self.base / 'dry'
        root = d.destination(dry, False)
        d.run([self.row], root)
        self.assertFalse(dry.exists())

    def test_hash_short_and_oversized(self):
        for payload in (b'bad', b'ab', b'abcd'):
            with self.subTest(payload=payload):
                root = d.destination(self.base / payload.decode(), True)
                with self.assertRaises(ValueError):
                    d.run([self.row], root, True, opener=Opener(payload))
                self.assertFalse((root / 'sub/a').exists())
                self.assertTrue((root / 'sub/a.part').exists())
                self.assertLessEqual((root / 'sub/a.part').stat().st_size, 3)

    def test_insufficient_space(self):
        with patch.object(d.os, 'statvfs', return_value=SimpleNamespace(f_bavail=d.EXTRA+d.RESERVE+2, f_frsize=1)):
            with self.assertRaises(ValueError):
                self.run_download()
        self.assertFalse((self.root / 'sub').exists())

    def test_interrupt_and_part_not_reused(self):
        with self.assertRaises(KeyboardInterrupt):
            self.run_download(Opener(interrupt=True))
        self.assertTrue((self.root / 'sub/a.part').exists())
        with self.assertRaises(FileExistsError):
            self.run_download()
        self.assertFalse((self.root / 'sub/a').exists())

    def test_bounded_retries(self):
        from unittest.mock import Mock
        opener = Mock()
        opener.open.side_effect = TimeoutError
        with self.assertRaises(TimeoutError):
            self.run_download(opener)
        self.assertEqual(opener.open.call_count, 3)

    def test_url_pinned(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(d.url_for(dict(self.row, Revision='master')))
        self.assertEqual(u.scheme, 'https')
        self.assertEqual(u.netloc, 'modelscope.cn')
        self.assertEqual(parse_qs(u.query)['Revision'], [d.REVISION])

    def test_publication_never_clobbers(self):
        original_link = d.os.link
        def racing_link(src, dst):
            Path(dst).write_bytes(b'other owner')
            return original_link(src, dst)
        with patch.object(d.os, 'link', side_effect=racing_link):
            with self.assertRaises(FileExistsError):
                self.run_download()
        self.assertEqual((self.root / 'sub/a').read_bytes(), b'other owner')
        self.assertEqual((self.root / 'sub/a.part').read_bytes(), b'abc')

    def test_redirect_refused(self):
        req = d.urllib.request.Request(d.url_for(self.row))
        for url in ('http://evil/', 'https://evil/',
                    'http://cdn-lfs-cn-1.modelscope.cn/a',
                    'https://cdn-lfs-cn-1.modelscope.cn.evil/a',
                    'https://user:pass@cdn-lfs-cn-1.modelscope.cn/a',
                    'https://cdn-lfs-cn-1.modelscope.cn:444/a'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                d.NoRedirect().redirect_request(req, None, 302, '', {}, url)

    def test_reviewed_cdn_and_no_forwarded_credentials(self):
        req = d.urllib.request.Request(d.url_for(self.row), headers={'Authorization': 'secret'})
        target = 'https://cdn-lfs-cn-1.modelscope.cn/blob?signature=example'
        redirected = d.NoRedirect().redirect_request(req, None, 302, '', {}, target)
        self.assertEqual(redirected.full_url, target)
        self.assertFalse(redirected.has_header('Authorization'))
        bad = d.urllib.request.Request(d.url_for(self.row).replace(d.REVISION, 'master'))
        with self.assertRaises(ValueError):
            d.NoRedirect().redirect_request(bad, None, 302, '', {}, target)

    def test_short_response_automatically_resumes_with_bounded_retry(self):
        class TruncatedThenRange:
            calls = 0
            def open(inner, request, timeout):
                inner.calls += 1
                if inner.calls == 1:
                    return Response(b'ab')
                self.assertEqual(request.get_header('Range'), 'bytes=2-')
                response = Response(b'c')
                response.getcode = lambda: 206
                response.headers = {'Content-Range': 'bytes 2-2/3'}
                return response
        opener = TruncatedThenRange()
        d.run([self.row], self.root, True, opener=opener, retries=1)
        self.assertEqual(opener.calls, 2)
        self.assertEqual((self.root / 'sub/a').read_bytes(), b'abc')

    def test_resume_ranges_and_hash(self):
        for status, header, prefix, succeeds in (
            (206, 'bytes 1-2/3', b'a', True),
            (206, 'bytes 0-2/3', b'a', False),
            (200, 'bytes 1-2/3', b'a', False),
            (206, 'bytes 1-2/3', b'x', False),
        ):
            with self.subTest(status=status, header=header, prefix=prefix):
                root = d.destination(self.base / ('case' + str(len(list(self.base.iterdir())))), True)
                part = root / 'sub/a.part'
                part.parent.mkdir()
                part.write_bytes(prefix)
                class RangeOpener:
                    def open(inner, request, timeout):
                        self.assertEqual(request.get_header('Range'), 'bytes=1-')
                        response = Response(b'bc')
                        response.getcode = lambda: status
                        response.headers = {'Content-Range': header}
                        return response
                if succeeds:
                    d.run([self.row], root, True, opener=RangeOpener(), resume=True)
                    self.assertEqual((root / 'sub/a').read_bytes(), b'abc')
                else:
                    with self.assertRaises(ValueError):
                        d.run([self.row], root, True, opener=RangeOpener(), resume=True)
                    self.assertTrue(part.exists())
                    self.assertFalse((root / 'sub/a').exists())

    def test_complete_and_empty_part(self):
        part = self.root / 'sub/a.part'
        part.parent.mkdir()
        part.write_bytes(b'abc')
        opener = Opener()
        d.run([self.row], self.root, True, opener=opener, resume=True)
        self.assertEqual(opener.calls, 0)
        (self.root / 'sub/a').unlink()
        part.touch()
        class EmptyRangeOpener:
            def open(inner, request, timeout):
                self.assertEqual(request.get_header('Range'), 'bytes=0-')
                response = Response(b'abc')
                response.getcode = lambda: 206
                response.headers = {'Content-Range': 'bytes 0-2/3'}
                return response
        d.run([self.row], self.root, True, opener=EmptyRangeOpener(), resume=True)
        self.assertEqual((self.root / 'sub/a').read_bytes(), b'abc')

    def test_lock_not_removed_when_foreign(self):
        lock = self.root / 'sub/a.part.lock'
        lock.parent.mkdir()
        lock.write_text('foreign PID')
        with self.assertRaises(FileExistsError):
            self.run_download()
        self.assertEqual(lock.read_text(), 'foreign PID')

    def test_parallel_budget_and_files(self):
        rows = [dict(self.row, Path=str(i)) for i in range(8)]
        with patch.object(d.os, 'statvfs', return_value=SimpleNamespace(
                f_bavail=d.EXTRA+d.RESERVE+24, f_frsize=1)):
            d.run(rows, self.root, True, opener=Opener(), workers=4)
        for row in rows:
            self.assertEqual((self.root / row['Path']).read_bytes(), b'abc')
        self.assertFalse(list(self.root.glob('*.lock')))

    def test_cdn_range_only(self):
        req = d.urllib.request.Request(d.url_for(self.row), headers={
            'Range': 'bytes=1-', 'Cookie': 'secret', 'Authorization': 'secret'})
        redirected = d.NoRedirect().redirect_request(req, None, 302, '', {},
            'https://cdn-lfs-cn-1.modelscope.cn/blob?signature=secret')
        self.assertEqual(dict(redirected.header_items()), {'Range': 'bytes=1-'})

    def test_failure_stops_submission(self):
        opener = Opener(b'bad')
        with self.assertRaises(ValueError):
            d.run([dict(self.row, Path=str(i)) for i in range(10)], self.root,
                  True, opener=opener, workers=1)
        self.assertEqual(opener.calls, 1)

    def test_max_files(self):
        opener = Opener()
        d.run([self.row, dict(self.row, Path='b')], self.root, True, 1, opener)
        self.assertEqual(opener.calls, 1)
        self.assertFalse((self.root / 'b').exists())


if __name__ == '__main__':
    unittest.main()
