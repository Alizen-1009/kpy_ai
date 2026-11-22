import json,hashlib,subprocess,sys,shutil,datetime,uuid,time,http.client
from pathlib import Path
staging={'deployment': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_yh', 'files': [{'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/scripts/vllm_ascend_repro/launch.py', 'sha256': '55f6dfaa467be07a29cbebb28d7453e7a61c272dd3a830af7096d63206199a78'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/scripts/vllm_ascend_repro/container_gate.py', 'sha256': '233e00a11121c123f664124d1e175d6433188d2d2e453db7be4429e9d79757d3'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/scripts/vllm_ascend_repro/download_assets.py', 'sha256': '32a59ee9f1a77d6680fd8d02c5c3df27de472c51984661692859729cc40e9d68'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/scripts/vllm_ascend_repro/reassemble_engram.py', 'sha256': '2424871224413ce712a60758d5fb75d9afb2dc829189cf476775a0a4bf53201f'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/scripts/vllm_ascend_repro/probe_service.py', 'sha256': 'e47f9ef3b6aae2b097d7b94df8a199d644a176f59de3620b9f3346abddb89800'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/docs/evidence/ascend910c/vllm-reproduction/launch/runtime-map.json', 'sha256': 'f63be58137f6615c843dbe6cc38bbc2f94354da6c3f8f9fbe02f6aa577aaab3e'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/docs/evidence/ascend910c/vllm-reproduction/image/runtime/runtime_report.json', 'sha256': '007d5805c683e79d1a7221b97a5e5f802f3b4d89be3b52f34ddc795707202ca7'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/docs/evidence/ascend910c/vllm-reproduction/p0-asset-inventory/public/model-files.json', 'sha256': '62e252b4a6d8eb23a89b0f2af65960d564711230bb1aba8b788e8936d5ed927c'}, {'path': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_v2_yh/docs/evidence/ascend910c/vllm-reproduction/p0-asset-inventory/public/metadata/engram_int8/PARTS.sha256', 'sha256': 'baba958502a4a6dc96f2e2e391eab4bff9baed1ec9ccc796fa4fc1e2b54ced78'}]}
frozen=[{'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/engram_hbm.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/engram_hbm.py', 'sha256': 'f8a762a93b932bbf655cc8edea20c637655d0579775f2aeceb5bdd6653401269'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/engram_hash.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/engram_hash.py', 'sha256': 'acf1aa4a9a75eef5ebe6dbf69bbeb8dd9195797c739ecc46751e3a79776ff4a8'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/engram_jit_kernel.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/engram_jit_kernel.py', 'sha256': '1394bbe7e9752a0bcf3cc177f3ff3baf10c9c1d6847569855f5d5ed5237f38cf'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/engram_plan_kernel.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/engram_plan_kernel.py', 'sha256': '87fd738eeb8c69d363d01105de1bb7067acc714e8d8e98739f146b6c547e8117'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/engram_gate.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/engram_gate.py', 'sha256': '955e40b94e933aabddb37035ec295e701bdfe3c12fef586a6b7ba775a05e90a2'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/model.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/model.py', 'sha256': 'dfbc3c0d3b0f9ce3349509de5dfb3799a47f834eec26a951769bf4a54e6c022b'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/ascend_forward_context.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/ascend_forward_context.py', 'sha256': 'eb8442f593c11d666743c18b0936e64a302e53b2d0972c691706b179efb3bdee'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/rope_dsv4.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/rope_dsv4.py', 'sha256': '25151bcf62e49e1c1db780718eb7c29322c51767bf15693b46fe7b34ed3ba981'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/dsa_v1.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/dsa_v1.py', 'sha256': 'f2633fd764203b14beff046a8029b48f4585d57df38914895be1cd432f41612c'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/patches/files/token_dispatcher_moemask.py', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/token_dispatcher_moemask.py', 'sha256': '37f96f834b98e257b5b82eaab607c451199b191c9c01078f61213c4e592fc9b8'}, {'source': 'ref/deepseek-v4.1-flash-ascend910B/scripts/serve_v2.sh', 'destination': '/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_584e300ab3594275976e6ec7c68281ed/serve_v2.sh', 'sha256': '814ef3abd53d7413653e2e2ac7c0b0bef83becff461996f93414de0a17106114'}]
base=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
dep=base/'deployment_v2_yh'; scripts=dep/'scripts/vllm_ascend_repro'; docs=dep/'docs/evidence/ascend910c/vllm-reproduction'
runid='p1-vision1-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
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
 payload=base/'payload'/'p1-20261121T203514Z-4f842308'
 assert payload.is_dir()
 runs=base/'runs_yh'; runs.mkdir(mode=0o700,exist_ok=True); task=runs/runid
 recovery=base/'logs/recovery-3-20261121T200226Z'
 argv=['python3','-B',str(scripts/'launch.py'),'--execute','--run-dir',str(task),'--model',str(base/'model'),'--payload-dir',str(payload),'--image-id','sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef','--run-id',runid,'--port','18550','--manifest',str(docs/'p0-asset-inventory/public/model-files.json'),'--verified-report',str(recovery/'verified_report.json'),'--reassembly-report',str(recovery/'reassembly.json'),'--runtime-report',str(docs/'image/runtime/runtime_report-vision1.json')]
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
