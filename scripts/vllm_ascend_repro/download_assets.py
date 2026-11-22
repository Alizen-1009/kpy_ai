"""Bounded pinned ModelScope downloader (dry-run, one worker by default).

Failed parts are retained; --resume explicitly permits validated range continuation.
Redirects allow only the observed ModelScope HTTPS CDN; signed URLs are never logged.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import threading
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

REVISION = '50029772e7757c3d9cec50481661091b369af901'
MODEL = 'chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend'
MARKER = '.vllm-ascend-assets-owner.json'
OWNER = {'model': MODEL, 'revision': REVISION, 'format': 1}
EXTRA = 196613849824
RESERVE = 64 * 1024**3
DEFAULT_MANIFEST = Path(__file__).resolve().parents[2] / 'docs/evidence/ascend910c/vllm-reproduction/p0-asset-inventory/public/model-files.json'


LOG_LOCK = threading.Lock()


def log(event, **fields):
    with LOG_LOCK:
        print(json.dumps({'event': event, **fields}), flush=True)


def inventory(path):
    rows = json.loads(Path(path).read_text())
    if not isinstance(rows, list):
        raise ValueError('manifest must be a list')
    seen = set()
    for row in rows:
        p = row['Path']
        if (not isinstance(p, str) or not p or '\\' in p or '\x00' in p
                or any(x in ('', '.', '..') for x in p.split('/'))
                or p.startswith('/') or p in seen or MARKER in p.split('/')
                or any(x.endswith(('.part', '.part.lock')) for x in p.split('/'))):
            raise ValueError('unsafe or duplicate path')
        if type(row['Size']) is not int or row['Size'] < 0:
            raise ValueError('invalid size')
        if not isinstance(row['Sha256'], str) or not re.fullmatch('[0-9a-fA-F]{64}', row['Sha256']):
            raise ValueError('invalid sha256')
        seen.add(p)
    for p in seen:
        if any(str(parent) in seen for parent in Path(p).parents if str(parent) != '.'):
            raise ValueError('file/directory conflict')
    return rows


def safe(path):
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError('symlink forbidden')


def destination(path, execute):
    root = Path(os.path.abspath(path))
    safe(root)
    marker = root / MARKER
    if root.exists():
        if not root.is_dir():
            raise ValueError('destination not directory')
        safe(marker)
        if marker.exists():
            if json.loads(marker.read_text()) != OWNER:
                raise ValueError('foreign marker')
            return root
        if any(root.iterdir()):
            raise ValueError('nonempty destination without marker')
    if execute:
        root.mkdir(parents=True, exist_ok=True)
        with marker.open('x') as f:
            json.dump(OWNER, f)
    return root


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def url_for(row):
    return ('https://modelscope.cn/api/v1/models/' + MODEL + '/repo?' +
            urllib.parse.urlencode({'Revision': REVISION, 'FilePath': row['Path']}))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Retain legacy class name; permit only the reviewed ModelScope CDN."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        source = urllib.parse.urlsplit(req.full_url)
        target = urllib.parse.urlsplit(newurl)
        allowed = {'modelscope.cn', 'cdn-lfs-cn-1.modelscope.cn'}
        if (source.scheme != 'https' or source.hostname not in allowed
                or target.scheme != 'https'
                or target.hostname != 'cdn-lfs-cn-1.modelscope.cn'
                or target.username is not None or target.password is not None
                or target.port not in (None, 443) or target.fragment
                or code not in (301, 302, 303, 307, 308)):
            raise ValueError('redirect forbidden')
        if source.hostname == 'modelscope.cn':
            query = urllib.parse.parse_qs(source.query)
            if (source.path != '/api/v1/models/' + MODEL + '/repo'
                    or query.get('Revision') != [REVISION]):
                raise ValueError('unpinned redirect source')
        # No inherited headers: never forward credentials to the CDN.
        headers = {}
        if req.has_header('Range'):
            headers['Range'] = req.get_header('Range')
        log('redirect', host=target.hostname, status=code)
        return urllib.request.Request(newurl, headers=headers, method='GET')


class ShortResponseError(ValueError):
    """Clean transport EOF before the manifest byte count; safe to Range-resume."""


def run(rows, root, execute=False, max_files=None, opener=None, timeout=60, retries=2,
        workers=1, resume=False):
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError('invalid workers')
    pending = []
    for row in rows:
        target = root / row['Path']
        safe(target)
        safe(Path(str(target) + '.part'))
        if target.exists():
            if not target.is_file() or target.stat().st_size != row['Size'] or digest(target) != row['Sha256'].lower():
                raise ValueError('existing file mismatch')
            log('verified_existing', path=row['Path'])
        else:
            pending.append(row)
    remaining = sum(row['Size'] for row in pending)
    for row in pending:
        part = Path(str(root / row['Path']) + '.part')
        if part.exists():
            if not resume:
                raise FileExistsError('retained part requires explicit resume')
            if not part.is_file() or part.stat().st_size > row['Size']:
                raise ValueError('invalid part size')
            remaining -= part.stat().st_size
    budget = threading.Lock()

    def check_space():
        space = os.statvfs(root)
        if space.f_bavail * space.f_frsize < remaining + EXTRA + RESERVE:
            raise ValueError('insufficient space')

    if execute:
        check_space()

    def download(row):
        nonlocal remaining
        log('download' if execute else 'planned', path=row['Path'], size=row['Size'])
        if not execute:
            return
        safe(root / row['Path'])
        target = root / row['Path']
        target.parent.mkdir(parents=True, exist_ok=True)
        part = Path(str(target) + '.part')
        safe(part)
        lock = Path(str(part) + '.lock')
        safe(lock)
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, str(os.getpid()).encode())
            for attempt in range(retries + 1):
                try:
                    transfer(row, target, part, resume or attempt > 0)
                    break
                except ShortResponseError:
                    log('short_response', path=row['Path'], retained_bytes=part.stat().st_size,
                        attempt=attempt + 1)
                    if attempt == retries:
                        raise
        finally:
            os.close(fd)
            lock.unlink()

    def transfer(row, target, part, allow_resume):
        nonlocal remaining
        if target.exists():
            raise FileExistsError('target appeared')
        h = hashlib.sha256()
        count = 0
        exists = part.exists()
        if exists:
            if not allow_resume:
                raise FileExistsError('retained part requires explicit resume')
            with part.open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    count += len(chunk)
                    if count > row['Size']:
                        raise ValueError('oversized part')
                    h.update(chunk)
        if exists and count == row['Size']:
            if h.hexdigest() != row['Sha256'].lower():
                raise ValueError('size/hash mismatch')
            os.link(part, target)
            part.unlink()
            log('complete', path=row['Path'], size=count)
            return
        request = url_for(row)
        if exists:
            request = urllib.request.Request(request, headers={'Range': f'bytes={count}-'})
        response = None
        for attempt in range(retries + 1):
            try:
                response = opener.open(request, timeout=timeout)
                break
            except OSError:
                if attempt == retries:
                    raise
                log('connection_retry', path=row['Path'], attempt=attempt + 1)
        with response:
            if exists:
                expected = f"bytes {count}-{row['Size'] - 1}/{row['Size']}"
                if response.getcode() != 206 or response.headers.get('Content-Range') != expected:
                    raise ValueError('invalid range response')
            elif response.getcode() != 200:
                raise ValueError('unexpected HTTP status')
            with part.open('ab' if exists else 'xb', buffering=0) as out:
                while True:
                    if stopped.is_set():
                        raise InterruptedError('download group stopped; partial retained')
                    chunk = response.read(min(1024 * 1024, row['Size'] - count + 1))
                    if not chunk:
                        break
                    if count + len(chunk) > row['Size']:
                        raise ValueError('oversized response')
                    with budget:
                        check_space()
                        written = out.write(chunk)
                        remaining -= written
                        if written != len(chunk):
                            raise OSError('short write')
                    count += len(chunk)
                    h.update(chunk)
                if count != row['Size']:
                    raise ShortResponseError('short response; partial retained')
                if h.hexdigest() != row['Sha256'].lower():
                    raise ValueError('size/hash mismatch')
                out.flush()
                os.fsync(out.fileno())
        # Portable atomic no-clobber publication. Same inode, never a second cache.
        os.link(part, target)
        part.unlink()
        log('complete', path=row['Path'], size=row['Size'])

    stopped = threading.Event()

    def task(row):
        if stopped.is_set():
            return
        try:
            download(row)
        except BaseException as exc:
            safe_reasons = {
                'insufficient space', 'oversized response', 'size/hash mismatch',
                'invalid range response', 'unexpected HTTP status',
                'redirect forbidden', 'unpinned redirect source', 'oversized part',
                'target appeared', 'short write',
                'download group stopped; partial retained', 'short response; partial retained',
            }
            reason = str(exc) if str(exc) in safe_reasons else 'details_redacted'
            log('file_failed', path=row['Path'], error_type=type(exc).__name__, reason=reason)
            stopped.set()
            raise

    selected = iter(pending[:max_files])
    with ThreadPoolExecutor(max_workers=workers) as pool:
        active = set()
        try:
            for row in selected:
                active.add(pool.submit(task, row))
                if len(active) == workers:
                    break
            while active:
                done, active = wait(active, return_when=FIRST_COMPLETED)
                for future in done:
                    future.result()
                for _ in done:
                    row = next(selected, None)
                    if row is not None and not stopped.is_set():
                        active.add(pool.submit(task, row))
        except BaseException:
            stopped.set()
            for future in active:
                future.cancel()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--dest', required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--direct', '--no-proxy', action='store_true')
    parser.add_argument('--max-files', type=int)
    parser.add_argument('--timeout', type=float, default=60)
    parser.add_argument('--retries', type=int, default=2)
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=1)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if not 0 < args.timeout <= 3600 or not 0 <= args.retries <= 5 or (args.max_files is not None and args.max_files < 1):
        parser.error('invalid timeout/retries/max-files')
    try:
        rows = inventory(args.manifest)
        root = destination(args.dest, args.execute)
        handlers = [NoRedirect()]
        if args.direct:
            handlers.append(urllib.request.ProxyHandler({}))
        run(rows, root, args.execute, args.max_files,
            urllib.request.build_opener(*handlers), args.timeout, args.retries,
            args.workers, args.resume)
        return 0
    except KeyboardInterrupt:
        log('interrupted')
        return 130
    except Exception as exc:
        # Never expose URLs, proxy credentials, or arbitrary exception text.
        log('failed', error_type=type(exc).__name__)
        return 1


if __name__ == '__main__':
    sys.exit(main())
