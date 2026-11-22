import json,hashlib,subprocess,sys,shutil,datetime,uuid,time,http.client
from pathlib import Path
staging=STAGING_JSON
frozen=FROZEN_JSON
base=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
dep=base/'deployment_yh'; scripts=dep/'scripts/vllm_ascend_repro'; docs=dep/'docs/evidence/ascend910c/vllm-reproduction'
runid='p1-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
ev=base/'logs'/runid; ev.mkdir(mode=0o700)
print('EVIDENCE',ev,flush=True)
def save(n,v): (ev/n).write_text(json.dumps(v,indent=2) if not isinstance(v,str) else v)
def cmd(a): return subprocess.run(a,text=True,capture_output=True,check=True).stdout
cid=None
try:
 hashes=[]
 for f in staging['files']:
  h=hashlib.sha256(Path(f['path']).read_bytes()).hexdigest(); hashes.append(dict(path=f['path'],sha256=h)); assert h==f['sha256'],f
 save('hashes.json',hashes)
 sys.path.insert(0,str(scripts)); import launch
 npu=cmd(['npu-smi','info']); save('preflight-npu.txt',npu); launch.check_npu(npu)
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
 disk=shutil.disk_usage(base).free
 ports=cmd(['ss','-H','-ltnp','sport = :18550']); save('preflight.json',dict(mem_available=mem,disk_free=disk,ports=ports)); assert mem>=64*1024**3 and disk>=64*1024**3 and not ports.strip()
 # Correct invocation layout without modifying any frozen original or staged tool.
 payload=base/'payload'/runid; payload.mkdir(mode=0o700)
 mapping=json.loads(launch.MAP.read_text())
 for m in mapping['mounts']:
  if not m['selected']: continue
  f=next(f for f in frozen if f['sha256']==m['sha256'])
  src=Path(f['destination']); assert hashlib.sha256(src.read_bytes()).hexdigest()==f['sha256'] and src.stat().st_mode&0o222==0
  dst=payload/m['source_relative_to_ref']; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst); dst.chmod(0o444)
 runs=base/'runs_yh'; runs.mkdir(mode=0o700,exist_ok=True); task=runs/runid
 recovery=base/'logs/recovery-3-20261121T200226Z'
 argv=['python3','-B',str(scripts/'launch.py'),'--execute','--run-dir',str(task),'--model',str(base/'model'),'--payload-dir',str(payload),'--image-id','sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef','--run-id',runid,'--port','18550','--manifest',str(docs/'p0-asset-inventory/public/model-files.json'),'--verified-report',str(recovery/'verified_report.json'),'--reassembly-report',str(recovery/'reassembly.json'),'--runtime-report',str(docs/'image/runtime/runtime_report.json')]
 save('argv.json',argv); save('run.json',dict(runid=runid,run_dir=str(task),payload=str(payload)))
 result=subprocess.run(argv,capture_output=True,text=True); save('launch.stdout',result.stdout); save('launch.stderr',result.stderr)
 if (task/'container.cid').exists():
  cid=(task/'container.cid').read_text().strip(); save('container.cid',cid); shutil.copyfile(task/'inspect.json',ev/'create-inspect.json')
 assert result.returncode==0,result.stdout+result.stderr
 deadline=time.monotonic()+1800
 while time.monotonic()<deadline:
  state=json.loads(cmd(['docker','inspect',cid]))[0]; save('inspect.json',state)
  logs=subprocess.run(['docker','logs',cid],capture_output=True,text=True); save('container.log',logs.stdout+logs.stderr)
  with (ev/'monitor.jsonl').open('a') as f: f.write(json.dumps(dict(time=time.time(),state=state['State'],meminfo=Path('/proc/meminfo').read_text()))+'\n')
  assert state['State']['Running'],'container exited'
  ports=cmd(['ss','-H','-ltnp','sport = :18550']); save('listeners.txt',ports)
  if ports.strip(): assert all(l.split()[3]=='127.0.0.1:18550' for l in ports.splitlines()),'non-loopback listener'
  ready=False
  try:
   c=http.client.HTTPConnection('127.0.0.1',18550,timeout=5); c.request('GET','/health'); r=c.getresponse(); ready=r.status==200; r.read(); c.close()
  except OSError: pass
  if ready: break
  time.sleep(15)
 else: raise RuntimeError('readiness timeout 1800s')
 probe=['python3','-B',str(scripts/'probe_service.py'),'--base-url','http://127.0.0.1:18550','--expected-model',runid,'--run-id',runid,'--out',str(ev/'smoke'),'--timeout','180','--count','3','--max-tokens','128']
 save('probe-argv.json',probe); p=subprocess.run(probe,capture_output=True,text=True); save('probe.stdout',p.stdout+p.stderr); assert p.returncode==0,'smoke failed'
 save('RESULT.json',dict(status='ready_smoke_completed_retained_for_P2',cid=cid,runid=runid,stop=['docker','stop',cid]))
except Exception as e:
 save('RESULT.json',dict(status='failed',error=repr(e),cid=cid,runid=runid))
 if cid:
  rec=json.loads(cmd(['docker','inspect',cid]))[0]; save('failure-inspect.json',rec)
  assert rec['Id']==cid and rec['Config']['Labels']['run_id']==runid and rec['Config']['Labels']['owner']=='yuhao-vllm-repro'
  logs=subprocess.run(['docker','logs',cid],capture_output=True,text=True); save('container.log',logs.stdout+logs.stderr)
  p=subprocess.run(['docker','stop',cid],capture_output=True,text=True); save('stop.json',dict(argv=['docker','stop',cid],returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
 print('FAILED',repr(e),flush=True)
print('DONE',ev,flush=True)
