"""Local Code128 adapter. No real sandbox run has been performed.

Template (image must already be locally verified, including its Python runtime):
 python3 code128_client.py --base http://127.0.0.1:18550 --model MODEL \
   --image sha256:FULL_VERIFIED_IMAGE_ID --out NEW_RUN --execute
Omit --execute for a request-free plan. Docker/Python startup must not import torch.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'reference/experiments/delivery_matrix/workloads.py'
LABEL = 'code128.owner'


def workloads():
    spec = importlib.util.spec_from_file_location('code128_frozen', SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bounded(argv, data=b'', timeout=15, limit=1048576):
    # Disk-backed stdin avoids pipe deadlock; never contains host-executable code.
    with tempfile.TemporaryFile() as incoming:
        incoming.write(data)
        incoming.seek(0)
        proc = subprocess.Popen(argv, stdin=incoming, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        output = bytearray()
        deadline = time.monotonic() + timeout
        try:
            with selectors.DefaultSelector() as sel:
                sel.register(proc.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('subprocess timeout')
                    if not sel.select(remaining):
                        raise TimeoutError('subprocess timeout')
                    chunk = os.read(proc.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    output.extend(chunk)
                    if len(output) > limit:
                        raise ValueError('stdout limit exceeded')
            proc.wait(timeout=max(.001, deadline-time.monotonic()))
            if proc.returncode:
                raise RuntimeError(bytes(output).decode(errors='replace'))
            return bytes(output)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            proc.stdout.close()


def owned(cid, token):
    if not re.fullmatch('[0-9a-f]{64}', cid):
        raise ValueError('full container ID required')
    info = json.loads(bounded(['docker', 'inspect', '--type', 'container', cid]))[0]
    if info['Id'] != cid or info['Config']['Labels'].get(LABEL) != token:
        raise ValueError('container ownership mismatch')
    return info


def validate_sandbox(info, image):
    h, c = info['HostConfig'], info['Config']
    if (info['Image'] != image or h.get('Privileged') is not False
            or h.get('NetworkMode') != 'none' or h.get('ReadonlyRootfs') is not True
            or h.get('PidMode') not in ('', 'private') or h.get('IpcMode') != 'private'
            or h.get('Runtime') != 'runc' or h.get('Devices')
            or h.get('DeviceRequests') or h.get('DeviceCgroupRules') or h.get('CapAdd')
            or h.get('CapDrop') != ['ALL']
            or 'no-new-privileges' not in h.get('SecurityOpt', [])
            or h.get('Memory') != 256*1024**2 or h.get('MemorySwap') != 256*1024**2
            or h.get('NanoCpus') != 10**9 or h.get('PidsLimit') != 64
            or c.get('User') != '65534:65534'
            or h.get('Tmpfs') != {'/tmp': 'rw,noexec,nosuid,nodev,size=32m'}
            or any(m.get('Type') != 'tmpfs' or m.get('Destination') != '/tmp'
                   for m in info.get('Mounts', []))):
        raise ValueError('sandbox isolation mismatch')


def cleanup(cid, token):
    owned(cid, token)
    bounded(['docker', 'rm', '-f', cid])


# This trusted bootstrap executes ONLY inside Docker. Frozen scoring functions,
# extraction and child runner are reused, replacing only bwrap with outer Docker.
BOOT = '''import json, sys, types
p=json.load(sys.stdin)
w=types.ModuleType("frozen")
w.__file__="/tmp/reference/experiments/delivery_matrix/workloads.py"
sys.modules["frozen"]=w
exec(compile(p["source"], w.__file__, "exec"), w.__dict__)
w._sandbox_command=lambda temp: ([sys.executable, "-I", "-S", "-c", w._CHILD_RUNNER], "docker")
w.fixed_unit_cases=lambda task: p["cases"]
print(json.dumps(w.score_code_output(p["task"], p["output"], memory_mb=192)))
'''


def sandbox(image, task, output, cases):
    if not re.fullmatch('sha256:[0-9a-f]{64}', image):
        raise ValueError('explicit verified local image ID required')
    info = json.loads(bounded(['docker', 'image', 'inspect', image]))[0]
    if info['Id'] != image or info['Config'].get('Volumes'):
        raise ValueError('image mismatch or implicit image volumes')
    token = uuid.uuid4().hex
    cid = bounded(['docker', 'create', '--pull=never', '--label', LABEL+'='+token,
                   '--runtime=runc', '--network=none', '--read-only', '--cap-drop=ALL',
                   '--security-opt=no-new-privileges', '--memory=256m',
                   '--memory-swap=256m', '--cpus=1', '--pids-limit=64',
                   '--ipc=private', '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=32m',
                   '--user=65534:65534', '--workdir=/tmp', '--env=TMPDIR=/tmp',
                   '--env=HOME=/tmp', '--entrypoint=python3',
                   '-i', image, '-I', '-S', '-c', BOOT]).decode().strip()
    try:
        validate_sandbox(owned(cid, token), image)
        payload = dict(source=SOURCE.read_text(), task=task, output=output, cases=cases)
        return json.loads(bounded(['docker', 'start', '-i', cid],
                                 json.dumps(payload).encode(), timeout=10))
    finally:
        cleanup(cid, token)


def summary(rows):
    passed = sum(r['score']['passed'] for r in rows)
    total = sum(r['score']['total'] for r in rows)
    if total != 128 or not 0 <= passed <= 128:
        raise ValueError('invalid Code128 totals')
    return dict(passed=passed, total=total,
                tasks_passed=sum(r['score']['passed'] == r['score']['total'] for r in rows))


def wire_fields(response):
    return dict(usage=response.get('usage'),
                finish_reason=response['choices'][0].get('finish_reason'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', default='http://127.0.0.1:18550')
    p.add_argument('--model', required=True)
    p.add_argument('--image')
    p.add_argument('--out', type=Path, default=Path('code128-run'))
    p.add_argument('--execute', action='store_true')
    a = p.parse_args()
    u = urlsplit(a.base)
    if u.scheme != 'http' or u.hostname != '127.0.0.1' or u.username or u.password or u.path not in ('', '/') or u.query or u.fragment:
        p.error('only http://127.0.0.1:PORT is accepted')
    w = workloads()
    if not a.execute:
        print(json.dumps(dict(mode='plan', tasks=[t.task_id for t in w.CODE_TASKS], total=128)))
        return
    if not a.image or not re.fullmatch('sha256:[0-9a-f]{64}', a.image):
        p.error('--image must be an explicitly verified local sha256 image ID')
    a.out.mkdir(parents=True, exist_ok=False)
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            raise ValueError('redirect forbidden')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    rows = []
    for task in w.CODE_TASKS:
        request = dict(model=a.model, temperature=0, max_tokens=4096,
                       messages=[dict(role='user', content=w.build_code_prompt(task.task_id))])
        row = dict(task=task.task_id, request=request)
        path = a.out / (task.task_id+'.json')
        path.write_text(json.dumps(row, ensure_ascii=False, indent=2))
        try:
            req = urllib.request.Request(a.base.rstrip('/')+'/v1/chat/completions',
                                         json.dumps(request).encode(), {'Content-Type':'application/json'})
            try:
                with opener.open(req, timeout=180) as response:
                    row['http_status'] = response.status
                    raw = response.read(4194305)
            except urllib.error.HTTPError as exc:
                row['http_status'] = exc.code
                with exc:
                    raw = exc.read(4194305)
                (a.out / (task.task_id+'.response')).write_bytes(raw)
                raise
            (a.out / (task.task_id+'.response')).write_bytes(raw)
            if len(raw) > 4194304:
                raise ValueError('HTTP response too large')
            response = json.loads(raw)
            row.update(wire_fields(response))
            row['score'] = sandbox(a.image, task.task_id,
                                  response['choices'][0]['message']['content'],
                                  w.fixed_unit_cases(task.task_id))
        except Exception as exc:
            row['error'] = str(exc)
            row['score'] = dict(passed=0, total=len(w.fixed_unit_cases(task.task_id)), status='error')
        path.write_text(json.dumps(row, ensure_ascii=False, indent=2))
        rows.append(row)
    (a.out/'summary.json').write_text(json.dumps(summary(rows), indent=2))


if __name__ == '__main__':
    main()
