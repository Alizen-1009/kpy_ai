import json,hashlib,subprocess
from pathlib import Path
E=Path(__file__).resolve().parent; root=E.parents[5]; docs=E.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
meta=next(json.loads(l) for l in (E/'meta.stdout').read_text().splitlines() if l.startswith('{'))
assert meta['status']=='passed' and meta['count']==266
report=json.loads((docs/'image/runtime/runtime_report.json').read_text())
report['runtime_map_sha256']=sha(docs/'launch/runtime-map.json')
report['vision1_amendment']={'changes':{'VISION':['0','1'],'MM_LIMIT_IMAGES':['0','1']},'meta_evidence_sha256':sha(E/'meta.stdout'),'meta_scope':'Actual image ViT/aligner constructors on torch meta; 266 parameter names/shapes exactly equal checkpoint headers including biases. Wrapper not instantiated. No generation evidence. All prior prerequisites unchanged.'}
(E/'runtime_report-vision1.json').write_text(json.dumps(report,indent=2))
staging=json.loads((docs/'launch/staging.stdout').read_text())
base='/root/syf/data_yf/yuhao_vllm_ascend_repro_yh'
subprocess.run(['ssh','910c','python3','-c',"\"from pathlib import Path; import shutil; s=Path('"+base+"/deployment_yh'); d=Path('"+base+"/deployment_v2_yh'); assert not d.exists(); shutil.copytree(s,d)\""],check=True)
for local,rel in [(docs/'launch/runtime-map.json','launch/runtime-map.json'),(E/'runtime_report-vision1.json','image/runtime/runtime_report-vision1.json')]:
 subprocess.run(['scp',str(local),'910c:'+base+'/deployment_v2_yh/docs/evidence/ascend910c/vllm-reproduction/'+rel],check=True)
newfiles=[]
for f in staging['files']:
 f=dict(f);f['path']=f['path'].replace('/deployment_yh/','/deployment_v2_yh/')
 if f['path'].endswith('/launch/runtime-map.json'):f['sha256']=sha(docs/'launch/runtime-map.json')
 newfiles.append(f)
staging['files']=newfiles
code=(E.parent/'remote.py').read_text().replace('STAGING_JSON',repr(staging)).replace('FROZEN_JSON',repr(json.loads((docs/'image/runtime/frozen-payload.json').read_text())))
code=code.replace("dep=base/'deployment_yh'","dep=base/'deployment_v2_yh'").replace("runid='p1-'","runid='p1-vision1-'").replace("docs/'image/runtime/runtime_report.json'","docs/'image/runtime/runtime_report-vision1.json'")
start=code.index(" payload=base/'payload'/runid;")
end=code.index(" runs=base/'runs_yh'",start)
code=code[:start]+" payload=base/'payload'/'p1-20261121T203514Z-4f842308'\n assert payload.is_dir()\n"+code[end:]
(E/'remote.py').write_text(code)
with (E/'execution.stdout').open('w') as out: subprocess.run(['ssh','-o','ConnectTimeout=20','910c','python3 -u'],input=code,text=True,stdout=out,stderr=subprocess.STDOUT,check=True)
