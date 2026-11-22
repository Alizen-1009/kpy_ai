import os,sys,json,time,hashlib,subprocess,shutil
from pathlib import Path
p=Path(__file__).resolve().parent
r=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
rows=json.loads((r/'tools/model-files.json').read_text())
def save(name,data): (p/name).write_text(json.dumps(data,indent=2))
def stats():
 result={}
 for row in rows:
  f=r/'model'/row['Path']
  result[row['Path']] = ({'size':f.stat().st_size,'mtime_ns':f.stat().st_mtime_ns,'inode':f.stat().st_ino} if f.exists() else None)
 return result
def ident(pid): return {'pid':pid,'start_ticks':Path('/proc/'+str(pid)+'/stat').read_text().split()[21]}
meta={'supervisor':ident(os.getpid()),'started_unix':time.time(),'tool_sha256':hashlib.sha256((p/'download_assets.py').read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((r/'tools/model-files.json').read_bytes()).hexdigest()}
save('process.json',meta)
code=1
try:
 writers=[]
 for f in Path('/proc').glob('[0-9]*/cmdline'):
  if int(f.parent.name)==os.getpid(): continue
  try: args=f.read_bytes().split(b'\0')
  except OSError: continue
  if any(Path(a.decode(errors='replace')).name in ('download_assets.py','supervisor.py','reassemble_engram.py') for a in args): writers.append(str(f))
 locks=list((r/'model').rglob('*.lock'))
 before=stats(); save('before.json',before)
 missing=sum(max(0,row['Size']-((r/'model'/(row['Path']+'.part')).stat().st_size if (r/'model'/(row['Path']+'.part')).exists() else 0)) for row in rows if before[row['Path']] is None)
 assembly=sum(row['Size'] for row in rows if '.part-' in row['Path'])
 free=shutil.disk_usage(r).free
 save('preflight.json',{'writers':writers,'locks':[str(x) for x in locks],'free':free,'download_remaining':missing,'assembly':assembly,'reserve':64*1024**3})
 if writers or locks or free<missing+assembly+64*1024**3: raise RuntimeError('preflight blocked')
 args=[sys.executable,str(p/'download_assets.py'),'--manifest',str(r/'tools/model-files.json'),'--dest',str(r/'model'),'--workers','4','--resume','--direct','--retries','3','--execute']
 with (p/'download.jsonl').open('x') as out:
  child=subprocess.Popen(args,stdout=out,stderr=subprocess.STDOUT); meta['downloader']=ident(child.pid); meta['args']=args; save('process.json',meta); code=child.wait()
 save('after.json',stats())
except BaseException as exc: meta['error']=repr(exc)
save('exit.json',{'code':code,'ended_unix':time.time(),'identity':meta})
sys.exit(code)
