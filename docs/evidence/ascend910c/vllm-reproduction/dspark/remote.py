import pathlib,json,subprocess,hashlib,base64,shutil,time,urllib.request,traceback,statistics
m=MAP_INPUT; payload=PAYLOAD_INPUT; rid=RUN_INPUT
B=pathlib.Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh'); E=B/'quality-run'/rid; E.mkdir(); P=B/'payload'/rid; P.mkdir(); cid=None
old='ec301b67f2f8466a76aa46b1f064f3753b5925157fd1c69c23449915cb757d4e'
def run(a): return subprocess.check_output(a,text=True)
def save(n,v): (E/n).write_text(v if isinstance(v,str) else json.dumps(v,indent=2,ensure_ascii=False))
def get(p): return urllib.request.urlopen('http://127.0.0.1:18550'+p,timeout=15).read()
def logs(c,n):
 p=subprocess.run(['docker','logs',c],capture_output=True,text=True); save(n,p.stdout+p.stderr)
try:
 mounts=[]
 for x in m['mounts']:
  if not x['selected']: continue
  f=P/x['source_relative_to_ref']; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(base64.b64decode(payload[x['source_relative_to_ref']])); f.chmod(0o444); assert hashlib.sha256(f.read_bytes()).hexdigest()==x['sha256']; mounts+=['-v',str(f)+':'+x['destination']+':ro']
 assert len(mounts)==26
 probe='import ast,pathlib; '+ '; '.join('ast.parse(pathlib.Path('+repr(x['destination'])+').read_text())' for x in m['mounts'] if x['selected'] and x['destination'].endswith('.py'))+'; import vllm_ascend.spec_decode.dspark_proposer; print("DSPARK_IMPORT_OK")'
 a=['docker','run','--rm','--network','none','--entrypoint','bash',*mounts,m['provenance']['image_id'],'-lc','python3 -c '+__import__('shlex').quote(probe)]
 save('preflight-argv.json',a); p=subprocess.run(a,capture_output=True,text=True,timeout=300); save('preflight.log',p.stdout+p.stderr); needs_device=p.returncode!=0
 if needs_device: assert 'get_arch> returned NULL' in p.stderr,'unexpected no-device import failure' 
 state=json.loads(run(['docker','inspect',old]))[0]; save('old-inspect.json',state); assert state['Id']==old and state['State']['Running'] and state['Config']['Labels']['owner']=='yuhao-vllm-repro'
 models=json.loads(get('/v1/models')); assert [x['id'] for x in models['data']]==['p2-graph-20261121T230225Z']
 metrics=get('/metrics').decode(); save('old-metrics.txt',metrics)
 for line in metrics.splitlines():
  if not line.startswith('#') and ('vllm:num_requests_running{' in line or 'vllm:num_requests_waiting{' in line): assert float(line.rsplit(' ',1)[1])==0
 logs(old,'old-container.log'); run(['docker','stop',old]); save('fresh-npu.txt',run(['npu-smi','info']))
 if needs_device:
  import sys
  sys.path.insert(0,str(B/'deployment_graph_yh/scripts/vllm_ascend_repro')); import launch
  launch.check_npu((E/'fresh-npu.txt').read_text())
  probe_args=['docker','run','--rm','--network','none','--entrypoint','bash']
  for dev in state['HostConfig']['Devices']: probe_args+=['--device',dev['PathOnHost']+':'+dev['PathInContainer']+':'+dev['CgroupPermissions']]
  destinations={x['destination'] for x in m['mounts'] if x['selected']}
  for mount in state['Mounts']:
   if mount['Destination'] not in destinations: probe_args+=['-v',mount['Source']+':'+mount['Destination']+(':rw' if mount['RW'] else ':ro')]
  for env in state['Config']['Env']: probe_args+=['-e',env]
  probe_args+=mounts+[m['provenance']['image_id'],'-lc','python3 -c '+__import__('shlex').quote(probe)]
  save('device-preflight-argv.json',probe_args); p=subprocess.run(probe_args,capture_output=True,text=True,timeout=300); save('device-preflight.log',p.stdout+p.stderr); assert p.returncode==0,'device import preflight failed'
 D=B/'deployment_dspark_yh'; assert not D.exists(); shutil.copytree(B/'deployment_graph_yh',D)
 M=D/'docs/evidence/ascend910c/vllm-reproduction/launch/runtime-map.json'; M.write_text(json.dumps(m,indent=2)); save('runtime-map.json',m)
 R=D/'docs/evidence/ascend910c/vllm-reproduction/image/runtime/runtime_report-vision1.json'; rr=json.loads(R.read_text()); rr.update(runtime_map_sha256=hashlib.sha256(M.read_bytes()).hexdigest(),scope='API prerequisites with no-device draft import only; NOT DSpark runtime certification',graph_runtime_verified=False,dspark_runtime_verified=False); R.write_text(json.dumps(rr,indent=2)); save('runtime-report.json',rr)
 a=json.loads((B/'quality-run/graph-spec0/argv.json').read_text()); a=[v.replace('deployment_graph_yh','deployment_dspark_yh').replace('p2-graph-20261121T230225Z',rid) for v in a]; a[a.index('--payload-dir')+1]=str(P); save('argv.json',a)
 p=subprocess.run(a,capture_output=True,text=True); save('launch.log',p.stdout+p.stderr)
 C=B/'runs_yh'/rid/'container.cid'
 if C.exists(): cid=C.read_text().strip(); save('container.cid',cid)
 assert p.returncode==0,'launch gate failed'
 deadline=time.monotonic()+1800
 while True:
  state=json.loads(run(['docker','inspect',cid]))[0]; save('inspect.json',state); logs(cid,'container.log'); assert state['State']['Running'],'container exited'
  try: models=json.loads(get('/v1/models'))
  except Exception:
   assert time.monotonic()<deadline,'readiness timeout'; time.sleep(15); continue
  assert [x['id'] for x in models['data']]==[rid]; save('models.json',models); break
 text=(E/'container.log').read_text(); assert 'dspark' in text.lower() and 'Captur' in text,'missing DSpark/capture evidence'
 for i,msg in enumerate([[{'role':'user','content':'请用中文解释什么是矩阵乘法。'}],[{'role':'user','content':'Write a Python function to compute factorial, including an example.'}],[{'role':'user','content':'记住数字42。'},{'role':'assistant','content':'我记住了42。'},{'role':'user','content':'刚才的数字是多少？'}]]):
  body={'model':rid,'messages':msg,'temperature':0,'max_tokens':256}; raw=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18550/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'}),timeout=300).read(); save('smoke-'+str(i)+'.json',raw.decode()); d=json.loads(raw); assert d['choices'][0]['message']['content'] and d['usage']['completion_tokens']>0
 save('metrics-before.txt',get('/metrics').decode()); logs(cid,'before.log')
 bench=(E/'current-tps.py').read_text() if (E/'current-tps.py').exists() else None
 assert bench is not None,'benchmark script missing'
 p=subprocess.run(['python3',str(E/'current-tps.py')],capture_output=True,text=True,timeout=1800); save('speed.jsonl',p.stdout); save('speed.stderr',p.stderr); assert p.returncode==0,'benchmark failed'
 save('metrics-after.txt',get('/metrics').decode()); logs(cid,'container.log'); save('SUCCESS.json',{'cid':cid,'run':rid,'address':'http://127.0.0.1:18550','stop':['docker','stop',cid]})
except Exception:
 save('FAILURE.txt',traceback.format_exc()); print(traceback.format_exc(),flush=True)
 if cid:
  logs(cid,'container.log'); state=json.loads(run(['docker','inspect',cid]))[0]; save('failure-inspect.json',state)
  if state['Id']==cid and state['Config']['Labels'].get('owner')=='yuhao-vllm-repro': run(['docker','stop',cid])
print(str(E),flush=True)
