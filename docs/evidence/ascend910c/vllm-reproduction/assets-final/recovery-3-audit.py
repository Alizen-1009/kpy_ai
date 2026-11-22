import json,hashlib,sys
from pathlib import Path
r=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh'); p=r/'logs/recovery-3-20261121T200226Z'; model=r/'model'
def load(f): return json.loads(f.read_text())
def digest(f): return hashlib.sha256(f.read_bytes()).hexdigest()
rows=load(r/'tools/model-files.json'); before=load(p/'before.json'); after=load(p/'after.json'); events=[json.loads(x) for x in (p/'download.jsonl').read_text().splitlines()]
assert load(p/'exit.json')['code']==0
assert len(rows)==120
verified={}
for row in rows:
 name=row['Path']; matching=[e for e in events if e.get('path')==name and e['event'] in ('verified_existing','complete')]
 assert len(matching)==1,(name,matching)
 f=model/name; s=f.stat(); current={'size':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino}
 assert current==after[name] and s.st_size==row['Size'],name
 if matching[0]['event']=='verified_existing': assert before[name]==after[name],name
 verified[name]=row['Sha256'].lower()
report_path=p/'reassembly.json'; assembled=load(report_path)
independent={line.split()[1]:line.split()[0] for line in (p/'independent.sha256').read_text().splitlines()}
for entry in assembled:
 assert entry['status']=='complete'
 assert independent[str(model/entry['path'])]==entry['sha256']
 assert (model/entry['path']).stat().st_size==entry['bytes']
report={'schema_version':1,'model':str(model),'manifest_sha256':digest(r/'tools/model-files.json'),'reassembly_sha256':digest(report_path),'files':verified,'evidence':{'download_log_sha256':digest(p/'download.jsonl'),'downloader_sha256':digest(p/'download_assets.py'),'before_sha256':digest(p/'before.json'),'after_sha256':digest(p/'after.json'),'independent_final_sha256_file':digest(p/'independent.sha256'),'method':'downloader full-hash verified_existing and complete events; unchanged size/mtime_ns/inode; independent final streams'},'event_counts':{event:sum(e['event']==event for e in events) for event in sorted({e['event'] for e in events})}}
(p/'verified_report.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
