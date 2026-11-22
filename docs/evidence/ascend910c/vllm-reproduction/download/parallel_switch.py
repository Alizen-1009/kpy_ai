import os, signal, json, time, hashlib, subprocess
from pathlib import Path
r=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
p=2207298
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
s=Path(f'/proc/{p}/stat').read_text().split()
cmd=Path(f'/proc/{p}/cmdline').read_bytes().replace(b'\0',b' ').decode()
assert boot=='20bd7f0d-55e0-4cf5-b001-eab251f97b15' and s[21]=='175851895'
assert cmd.strip()==f'python3 -u {r}/tools/run_download_restart.py'
e={'old_pid':p,'old_start_ticks':s[21],'boot_id':boot,'old_cmdline':cmd,'termination_unix':time.time()}
os.kill(p,signal.SIGTERM)
for _ in range(100):
    q=Path(f'/proc/{p}/stat')
    if not q.exists() or q.read_text().split()[2]=='Z': break
    time.sleep(.1)
else: raise RuntimeError('old process remains')
writers=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit(): continue
    try:
        for fd in (proc/'fd').iterdir():
            try:
                target=os.readlink(fd)
                if target.startswith(str(r/'model')+'/'):
                    flags=int(next(x.split()[1] for x in (proc/'fdinfo'/fd.name).read_text().splitlines() if x.startswith('flags:')),8)
                    if flags & 3: writers.append({'pid':proc.name,'target':target})
            except (OSError,StopIteration): pass
    except OSError: pass
assert not writers, writers
e['writers']=writers
rows=json.loads((r/'tools/model-files.json').read_text()); assert len(rows)==120
complete=[]; parts={}; remaining=0
for row in rows:
    f=r/'model'/row['Path']; part=Path(str(f)+'.part')
    if f.exists():
        h=hashlib.sha256()
        with f.open('rb') as src:
            for chunk in iter(lambda:src.read(8*1024**2),b''): h.update(chunk)
        assert f.stat().st_size==row['Size'] and h.hexdigest()==row['Sha256'].lower()
        complete.append(row['Path'])
    else:
        n=part.stat().st_size if part.exists() else 0
        assert n<=row['Size']; remaining+=row['Size']-n
        if part.exists(): parts[row['Path']]=n
v=os.statvfs(r/'model'); available=v.f_bavail*v.f_frsize
required=remaining+196613849824+64*1024**3
e.update(complete=complete,parts=parts,remaining=remaining,available=available,required=required,space_pass=available>=required,manifest_sha256=hashlib.sha256((r/'tools/model-files.json').read_bytes()).hexdigest())
(r/'logs/parallel-preflight.json').write_text(json.dumps(e,indent=2))
assert available>=required
with (r/'logs/parallel-download.jsonl').open('xb') as out:
    child=subprocess.Popen(['python3','-u',str(r/'tools/run_download_parallel.py')],stdout=out,stderr=subprocess.STDOUT,start_new_session=True,stdin=subprocess.DEVNULL)
print(json.dumps({'launched_pid':child.pid,**e}))
