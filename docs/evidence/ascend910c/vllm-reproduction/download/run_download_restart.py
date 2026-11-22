"""Restart supervisor; logging does not relax reviewed download policy."""
import hashlib, json, os, sys, time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.error import HTTPError
import download_assets as d
root = Path(__file__).resolve().parents[1]
identity = {'pid': os.getpid(), 'start_ticks': Path('/proc/self/stat').read_text().split()[21], 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'started_unix': time.time(), 'script': str(Path(__file__).resolve()), 'tool_sha256': hashlib.sha256(Path(d.__file__).read_bytes()).hexdigest()}
(root / 'logs/restart-process.json').write_text(json.dumps(identity))
d.log('process', **identity)
original_redirect = d.NoRedirect.redirect_request
def diagnostic_redirect(self, req, fp, code, msg, headers, newurl):
    try:
        result = original_redirect(self, req, fp, code, msg, headers, newurl)
    except Exception as exc:
        d.log('redirect_refused', status=code, hostname=urlsplit(newurl).hostname, error_type=type(exc).__name__)
        raise
    d.log('redirect_allowed', status=code, hostname=urlsplit(newurl).hostname)
    return result
d.NoRedirect.redirect_request = diagnostic_redirect
original_run = d.run
def diagnostic_run(*args, **kwargs):
    try:
        return original_run(*args, **kwargs)
    except HTTPError as exc:
        d.log('http_error', status=exc.code)
        raise
d.run = diagnostic_run
sys.argv = ['download_assets.py', '--manifest', str(root / 'tools/model-files.json'), '--dest', str(root / 'model'), '--direct', '--execute']
code = d.main()
d.log('supervisor_exit', code=code)
(root / 'logs/restart-exit.json').write_text(json.dumps({'code': code, 'ended_unix': time.time()}))
sys.exit(code)
