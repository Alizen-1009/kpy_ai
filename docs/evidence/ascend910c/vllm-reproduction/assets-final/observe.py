import json, os, time
from pathlib import Path
root=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
end=time.monotonic()+14400
while time.monotonic()<end:
    proc=Path('/proc/2210671')
    alive=proc.exists()
    identity=alive and (proc/'stat').read_text().split()[21]=='175934799' and Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='20bd7f0d-55e0-4cf5-b001-eab251f97b15' and b'run_download_parallel.py' in (proc/'cmdline').read_bytes()
    exitfile=root/'logs/parallel-exit.json'
    exitdata=json.loads(exitfile.read_text()) if exitfile.exists() else None
    space=os.statvfs(root)
    files=[p for p in (root/'model').rglob('*') if p.is_file()]
    row={'time':time.time(),'alive':alive,'identity':identity,'exit':exitdata,'available':space.f_bavail*space.f_frsize,'bytes':sum(p.stat().st_size for p in files),'log_tail':(root/'logs/parallel-download.jsonl').read_text()[-1600:]}
    print(json.dumps(row),flush=True)
    if alive and not identity: raise SystemExit(31)
    if row['available']<68719476736: raise SystemExit(32)
    if not alive:
        if exitdata is None: raise SystemExit(33)
        raise SystemExit(0 if exitdata['code']==0 else 34)
    time.sleep(60)
raise SystemExit(124)
