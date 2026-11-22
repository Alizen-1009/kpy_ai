#!/usr/bin/env python3
"""Independent eager launcher. Reports are trusted operator attestations, not signatures.

Verification report v1: {schema_version:1, model:absolute-path,
manifest_sha256:hex, reassembly_sha256:hex, files:{relative-path:sha256}}.
Every inventory entry must occur exactly once; external verifier must hash all
bytes after reassembly. Runtime report v1: {schema_version:1,image_id:sha256:hex,
runtime_map_sha256:hex,cann_login_verified:true,payload_api_verified:true,
image_environment_verified:true,reviewed_image_env:{"PATH":"/usr/bin:/bin"},mapping:{"4":[8,9],..."7":[14,15]}}.
Runtime report is required independent read-only image verification evidence.
"""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path
try:
    from . import container_gate as gate, download_assets as assets, reassemble_engram as assembly
except ImportError:
    import container_gate as gate
    import download_assets as assets
    import reassemble_engram as assembly

MAP = Path(__file__).resolve().parents[2] / 'docs/evidence/ascend910c/vllm-reproduction/launch/runtime-map.json'
MAPPING = {str(i): [2*i, 2*i+1] for i in range(4, 8)}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    p = Path(value)
    require(p.is_absolute() and str(p) == value and not any(x in value for x in (',', '\n', '\x00')) and '..' not in p.parts, 'noncanonical source')
    require(not any(x.is_symlink() for x in (p, *p.parents)), 'symlink source')
    return p


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(canonical(str(p)).read_text())


def run(argv):
    return subprocess.run(argv, check=True, text=True, capture_output=True).stdout


def check_npu(text):
    pending = None
    seen, idle = set(), set()
    for line in text.splitlines():
        if not line.strip().startswith('|'):
            continue
        cells = [x.strip() for x in line.strip().strip('|').split('|')]
        header = re.fullmatch(r'(\d+)\s+Ascend910', cells[0])
        if header:
            require(pending is None and len(cells) == 3, 'unknown NPU header')
            pending = int(header[1])
            require(0 <= pending <= 7 and cells[1] == 'OK', 'unknown/unhealthy card')
            continue
        chip = re.fullmatch(r'([01])\s+(\d+)', cells[0])
        if chip:
            require(pending is not None and len(cells) == 3, 'orphan chip')
            c, die = int(chip[1]), int(chip[2])
            require(die == 2*pending+c and (pending,c) not in seen, 'mapping/duplicate chip')
            require(re.fullmatch(r'[0-9A-Fa-f]{4}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}\.\d', cells[1]), 'unknown PCI row')
            require(cells[2].split()[0].isdigit(), 'unknown utilization')
            if pending >= 4:
                require(cells[2].split()[0] == '0', 'busy AICore')
            seen.add((pending,c))
            pending = None
            continue
        empty = re.fullmatch(r'No running processes found in NPU ([0-7])', cells[0])
        if empty:
            card = int(empty[1])
            require(card not in idle and pending is None, 'duplicate idle')
            idle.add(card)
            continue
        # Header text only; any unknown numeric/process record fails closed.
        require(not re.match(r'\d', cells[0]) and not cells[0].startswith('No running') and pending is None, 'unknown/process row')
    require(pending is None and all((c,k) in seen for c in range(4,8) for k in (0,1)) and set(range(4,8)) <= idle, 'incomplete target table')


def env_dict(items):
    require(isinstance(items,list), 'invalid image ENV')
    result = {}
    for item in items:
        key, sep, value = item.partition('=')
        require(sep and key not in result, 'duplicate/invalid ENV')
        result[key] = value
    return result


def execute(args, mapping):
    for key in ('run_dir','model','payload_dir','image_id','run_id','port','manifest','verified_report','reassembly_report','runtime_report'):
        require(getattr(args, key) is not None, 'execute requires --'+key.replace('_','-'))
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', args.image_id), 'immutable image ID required')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,80}', args.run_id), 'invalid run ID')
    require(1024 <= args.port <= 65535, 'invalid port')
    task, model, payload = map(canonical, (args.run_dir,args.model,args.payload_dir))
    require(not task.exists() and task.parent.is_dir(), 'run directory must be new')
    for root in (model,payload):
        require(root.is_dir() and root not in task.parents and task not in root.parents, 'overlapping or absent inputs')
        require(not any(p.is_symlink() for p in root.rglob('*')), 'tree contains symlinks')
    require(load(model/assets.MARKER) == assets.OWNER, 'OWNER mismatch')
    manifest = canonical(args.manifest)
    rows = assets.inventory(manifest)
    report = load(args.verified_report)
    require(report.get('schema_version') == 1 and report.get('model') == str(model), 'verification binding mismatch')
    require(report.get('manifest_sha256') == digest(manifest) and report.get('reassembly_sha256') == digest(canonical(args.reassembly_report)), 'report digest mismatch')
    require(report.get('files') == {r['Path']:r['Sha256'].lower() for r in rows}, 'all manifest hashes must be verified')
    for r in rows:
        p = canonical(str(model/r['Path']))
        require(p.is_file() and p.stat().st_size == r['Size'], 'verified file missing or size changed')
    reassembled = load(args.reassembly_report)
    expected = assembly.plan(manifest)
    require(isinstance(reassembled,list) and len(reassembled) == 2, 'two reassembly results required')
    for entry,(target,sha,parts) in zip(reassembled,expected):
        size = sum(part['Size'] for part in parts)
        require(entry == dict(path=target,sha256=sha,bytes=size,status=entry.get('status')) and entry['status'] in ('complete','verified_existing'), 'reassembly incomplete/mismatch')
        output = canonical(str(model/target))
        require(output.is_file() and output.stat().st_size == size, 'assembled output missing/changed')
    runtime = load(args.runtime_report)
    require(runtime.get('schema_version') == 1 and runtime.get('image_id') == args.image_id and runtime.get('runtime_map_sha256') == digest(MAP) and runtime.get('mapping') == MAPPING, 'runtime evidence binding mismatch')
    require(all(runtime.get(k) is True for k in ('cann_login_verified','payload_api_verified','image_environment_verified')), 'runtime evidence incomplete')
    image = json.loads(run(['docker','image','inspect',args.image_id]))[0]
    require(image.get('Id') == args.image_id, 'image identity drift')
    reviewed = runtime.get('reviewed_image_env')
    require(isinstance(reviewed,dict) and env_dict(image['Config'].get('Env',[])) == reviewed, 'image ENV drift')
    require(not any(k in reviewed for k in ('LD_PRELOAD','LD_AUDIT','BASH_ENV','ENV')), 'unsafe image environment')
    mounts = [(str(model),str(model),False),('/usr/local/Ascend/driver','/usr/local/Ascend/driver',False)]
    for m in mapping['mounts']:
        if m['selected']:
            p = canonical(str(payload/m['source_relative_to_ref']))
            require(p.is_file() and digest(p) == m['sha256'] and p.stat().st_mode & 0o222 == 0, 'payload not frozen/hash mismatch')
            mounts.append((str(p),m['destination'],False))
    for src, _, _ in mounts:
        require(canonical(src).exists(), 'mount absent')
    run(['bash','-c',' && '.join('test -c '+p for p in sorted(gate.DEVICES))])
    check_npu(run(['npu-smi','info']))
    task.mkdir(mode=0o700)
    for name,dst in (('workspace','/workspace'),('cache','/numba_cache')):
        p = task/name
        p.mkdir(mode=0o700)
        mounts.append((str(p),dst,True))
    env = dict(mapping['environment_whitelist'], MODEL=str(model),PORT=str(args.port),SERVED_NAME=args.run_id,HOST='127.0.0.1')
    argv = ['docker','create','--label','owner=yuhao-vllm-repro','--label','run_id='+args.run_id,'--network','host','--ipc','private','--security-opt','no-new-privileges','--memory','768g','--cpus','64','--pids-limit','8192','--shm-size','16g']
    for d in sorted(gate.DEVICES):
        argv += ['--device',d+':'+d]
    for src,dst,rw in mounts:
        argv += ['--mount',f'type=bind,src={src},dst={dst}'+('' if rw else ',readonly')]
    for k,v in env.items():
        argv += ['--env',k+'='+v]
    # Login profiles may reintroduce empty search-path entries. Sanitize after
    # profile execution, immediately before the frozen serving script.
    bootstrap = (
        "import os; "
        "os.environ.update({k: ':'.join(v for v in os.environ.get(k, '').split(':') if v) "
        "for k in ('LD_LIBRARY_PATH', 'PYTHONPATH')}); "
        "os.execvp('bash', ['bash', '/opt/dsv41/scripts/serve_v2.sh'])"
    )
    command = ('printf %s 0 > /tmp/v41_engram_localowner && '
               'printf %s fast > /tmp/v41_hash_mode && cd /workspace && '
               'exec python3 -B -c ' + shlex.quote(bootstrap))
    argv += ['--entrypoint','bash',args.image_id,'-lc',command]
    cid = run(argv).strip()
    require(re.fullmatch('[0-9a-f]{64}',cid), 'invalid create CID: '+cid)
    (task/'container.cid').write_text(cid+'\n')
    print('Created CID (retained on failure): '+cid)
    record = json.loads(run(['docker','inspect','--type','container',cid]))[0]
    (task/'inspect.json').write_text(json.dumps(record,indent=2))
    errors = gate.validate_inspect(record,cid,args.image_id,args.run_id,[s for s,_,w in mounts if not w],[s for s,_,w in mounts if w])
    require(not errors, '; '.join(errors))
    host = record['HostConfig']
    require(host.get('NetworkMode') == 'host' and host.get('IpcMode') == 'private', 'namespace drift')
    require('no-new-privileges' in host.get('SecurityOpt', []), 'security option drift')
    require(host.get('Memory') == 768*1024**3 and host.get('NanoCpus') == 64*10**9 and host.get('PidsLimit') == 8192 and host.get('ShmSize') == 16*1024**3, 'resource limit drift')
    require({(m['Source'],m['Destination'],m['RW']) for m in record['Mounts']} == set(mounts), 'mount destination drift')
    actual_env = record['Config'].get('Env', [])
    require(env_dict(actual_env) == dict(reviewed, **env), 'container ENV drift')
    require(record['Config'].get('Entrypoint') == ['bash'] and record['Config'].get('Cmd') == ['-lc',command], 'command drift')
    check_npu(run(['npu-smi','info']))
    run(['docker','start',cid])
    return cid


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    p.add_argument('--execute',action='store_true')
    for k in ('run-dir','model','payload-dir','image-id','run-id','manifest','verified-report','reassembly-report','runtime-report'):
        p.add_argument('--'+k)
    p.add_argument('--port',type=int)
    a = p.parse_args(argv)
    mapping = load(MAP)
    if not a.execute:
        print(json.dumps({'mode':'plan','runtime_map':mapping,'required_reports':__doc__},indent=2))
        return 0
    try:
        execute(a,mapping)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as e:
        print('REFUSED: '+str(e))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
