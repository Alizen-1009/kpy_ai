"""Reuse the audited device lifecycle for help-only, no service or repeated op probes."""
from pathlib import Path
p = Path(__file__).with_name('device_preflight.py')
s = p.read_text()
a = s.index("probe=r'''")
b = s.index("probe='PAYLOADS='", a)
s = s[:a] + '''probe=r\'''import sys,runpy
sys.argv=['vllm','serve','--help=all']
try:
 runpy.run_module('vllm.entrypoints.cli.main',run_name='__main__')
except SystemExit as e:
 print('CLI_EXIT',e.code,flush=True)
 raise
\'''
''' + s[b:]
s = s.replace("'p1-device-preflight-'+uuid.uuid4().hex", "'cli-help-preflight-'+uuid.uuid4().hex")
exec(compile(s, str(p), 'exec'))
