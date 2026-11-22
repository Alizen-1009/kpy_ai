import json,time,hashlib
from pathlib import Path
r=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
i=json.loads((r/'logs/parallel-process.json').read_text())
p=Path('/proc')/str(i['pid'])
result={'unix':time.time(),'identity':i,'running':p.exists(),'parts':{str(x.relative_to(r/'model')):x.stat().st_size for x in (r/'model').rglob('*.part')},'locks':{str(x.relative_to(r/'model')):x.read_text() for x in (r/'model').rglob('*.part.lock')}}
if p.exists(): result.update(start_ticks=(p/'stat').read_text().split()[21],cmdline=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode())
rows=json.loads((r/'tools/model-files.json').read_text()); verified=[]
for row in rows:
 f=r/'model'/row['Path']
 if f.exists():
  h=hashlib.sha256()
  with f.open('rb') as src:
   for c in iter(lambda:src.read(8*1024**2),b''):h.update(c)
  assert f.stat().st_size==row['Size'] and h.hexdigest()==row['Sha256'].lower()
  verified.append(row['Path'])
result['verified_complete']=verified
result['exit']=json.loads((r/'logs/parallel-exit.json').read_text()) if (r/'logs/parallel-exit.json').exists() else None
print(json.dumps(result,indent=2))
