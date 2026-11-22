import os,sys,json,time,hashlib,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
r=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
args=[sys.executable,str(p/'download_assets.py'),'--manifest',str(r/'tools/model-files.json'),'--dest',str(r/'model'),'--workers','4','--resume','--direct','--execute']
def ident(pid):
 return {'pid':pid,'start_ticks':Path('/proc/'+str(pid)+'/stat').read_text().split()[21],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
meta={'supervisor':ident(os.getpid()),'started_unix':time.time(),'args':args,'recovery_path':str(p),'tool_sha256':hashlib.sha256((p/'download_assets.py').read_bytes()).hexdigest(),'supervisor_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((r/'tools/model-files.json').read_bytes()).hexdigest()}
(p/'process.json').write_text(json.dumps(meta,indent=2))
try:
 with (p/'download.jsonl').open('x') as out:
  child=subprocess.Popen(args,stdout=out,stderr=subprocess.STDOUT)
  meta['downloader']=ident(child.pid)
  (p/'process.json').write_text(json.dumps(meta,indent=2))
  code=child.wait()
except BaseException as exc:
 code=1
 meta['supervisor_error_type']=type(exc).__name__
(p/'exit.json').write_text(json.dumps({'code':code,'ended_unix':time.time(),'identity':meta},indent=2))
sys.exit(code)
