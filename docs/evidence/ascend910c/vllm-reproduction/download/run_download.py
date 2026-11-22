"""Owned supervisor: refuse redirects, logging only status and hostname."""
import json, os, sys, time
from pathlib import Path
from urllib.parse import urlsplit
import download_assets as d

root = Path(__file__).resolve().parents[1]

def refuse(self, req, fp, code, msg, headers, newurl):
    d.log('redirect_refused', status=code, hostname=urlsplit(newurl).hostname)
    raise ValueError('redirect forbidden')

d.NoRedirect.redirect_request = refuse
identity = {'pid': os.getpid(), 'start_ticks': Path('/proc/self/stat').read_text().split()[21], 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'started_unix': time.time(), 'script': str(Path(__file__).resolve())}
(root / 'logs/process.json').write_text(json.dumps(identity))
d.log('process', **identity)
base = ['download_assets.py', '--manifest', str(root / 'tools/model-files.json'), '--dest', str(root / 'model'), '--direct', '--execute']
sys.argv = base + ['--max-files', '3']
code = d.main()
if code == 0:
    rows = d.inventory(root / 'tools/model-files.json')
    for row in rows[:3]:
        p = root / 'model' / row['Path']
        assert p.stat().st_size == row['Size'] and d.digest(p) == row['Sha256'].lower()
    d.log('canary_verified', files=3, bytes=sum(r['Size'] for r in rows[:3]))
    sys.argv = base
    code = d.main()
d.log('supervisor_exit', code=code)
(root / 'logs/exit.json').write_text(json.dumps({'code': code, 'ended_unix': time.time()}))
sys.exit(code)
