import hashlib,json,os,sys,time,signal
from pathlib import Path
import download_assets_parallel as d
r=Path(__file__).resolve().parents[1]
identity={'pid':os.getpid(),'start_ticks':Path('/proc/self/stat').read_text().split()[21],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'started_unix':time.time(),'script':str(Path(__file__).resolve()),'tool_sha256':hashlib.sha256(Path(d.__file__).read_bytes()).hexdigest(),'args':['--workers','4','--resume','--direct','--execute']}
(r/'logs/parallel-process.json').write_text(json.dumps(identity,indent=2)); d.log('process',**identity)
def terminated(sig,frame):
    (r/'logs/parallel-exit.json').write_text(json.dumps({'code':128+sig,'ended_unix':time.time(),'signal':sig}))
    os._exit(128+sig)
signal.signal(signal.SIGTERM,terminated)
sys.argv=['download_assets_parallel.py','--manifest',str(r/'tools/model-files.json'),'--dest',str(r/'model'),'--workers','4','--resume','--direct','--execute']
code=d.main()
(r/'logs/parallel-exit.json').write_text(json.dumps({'code':code,'ended_unix':time.time()})); d.log('supervisor_exit',code=code)
sys.exit(code)
