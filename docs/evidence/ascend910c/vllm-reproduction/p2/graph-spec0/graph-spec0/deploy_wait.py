import pathlib,json,subprocess,hashlib,shutil,datetime,time,urllib.request,traceback
B=pathlib.Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh'); E=B/'quality-run/graph-spec0'; E.mkdir(exist_ok=True)
def run(a): return subprocess.check_output(a,text=True)
cid=None
try:
 old=json.loads(run(['docker','inspect','8bf3ddd996ee580b7d94629ad7aeaa6c6d2b4158580a50e25c734ad4fe57313c']))[0]; assert not old['State']['Running']; (E/'old-inspect.json').write_text(json.dumps(old))
 (E/'fresh-npu.txt').write_text(run(['npu-smi','info'])); ports=run(['ss','-lntp']); (E/'ports.txt').write_text(ports); assert ':18550 ' not in ports
 D=B/'deployment_graph_yh'; assert not D.exists(); shutil.copytree(B/'deployment_v3_yh',D)
 M=D/'docs/evidence/ascend910c/vllm-reproduction/launch/runtime-map.json'; prev=json.loads(M.read_text()); m=json.loads((E/'graph-runtime-map.json').read_text()); assert m['mounts']==prev['mounts']
 m['environment_whitelist'].update(MAX_LEN='8192',VISION='1',MM_LIMIT_IMAGES='1'); M.write_text(json.dumps(m,indent=2)+'\n'); (E/'graph-runtime-map8192.json').write_bytes(M.read_bytes())
 R=D/'docs/evidence/ascend910c/vllm-reproduction/image/runtime/runtime_report-vision1.json'; rr=json.loads(R.read_text()); rr.update(runtime_map_sha256=hashlib.sha256(M.read_bytes()).hexdigest(),scope='API prerequisites only; NOT graph capture/replay certification',graph_runtime_verified=False); R.write_text(json.dumps(rr,indent=2)+'\n'); (E/'runtime_report.json').write_bytes(R.read_bytes())
 a=json.loads((B/'quality-run/context8192/argv.json').read_text()); rid='p2-graph-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'); a=[v.replace('deployment_v3_yh','deployment_graph_yh').replace('p2-8192-20261121T224721Z',rid) for v in a]; (E/'argv.json').write_text(json.dumps(a)); (E/'run-id.txt').write_text(rid)
 p=subprocess.run(a,capture_output=True,text=True); (E/'launch.log').write_text(p.stdout+p.stderr); assert p.returncode==0,p.stdout+p.stderr
 cid=(B/'runs_yh'/rid/'container.cid').read_text().strip(); (E/'container.cid').write_text(cid)
 deadline=time.monotonic()+2700
 while True:
  state=json.loads(run(['docker','inspect',cid]))[0]; assert state['State']['Running'],state['State']
  p=subprocess.run(['docker','logs',cid],capture_output=True,text=True); (E/'container.log').write_text(p.stdout+p.stderr)
  try: models=json.load(urllib.request.urlopen('http://127.0.0.1:18550/v1/models',timeout=10))
  except Exception:
   assert time.monotonic()<deadline,'readiness deadline'; time.sleep(15); continue
  assert [x['id'] for x in models['data']]==[rid]; (E/'models.json').write_text(json.dumps(models)); break
 payload={'model':rid,'messages':[{'role':'user','content':'Reply only OK.'}],'max_tokens':8,'temperature':0}; req=urllib.request.Request('http://127.0.0.1:18550/v1/chat/completions',json.dumps(payload).encode(),{'Content-Type':'application/json'}); raw=urllib.request.urlopen(req,timeout=180).read(); (E/'smoke.response').write_bytes(raw); assert json.loads(raw)['choices'][0]['message']['content']; (E/'READY').write_text(rid)
except Exception:
 (E/'FAILURE.txt').write_text(traceback.format_exc()); print(traceback.format_exc())
 if cid:
  state=json.loads(run(['docker','inspect',cid]))[0]
  p=subprocess.run(['docker','logs',cid],capture_output=True,text=True); (E/'container.log').write_text(p.stdout+p.stderr)
  if not (E/'READY').exists() and state['Id']==cid and state['Config']['Labels'].get('owner')=='yuhao-vllm-repro': run(['docker','stop',cid])
finally:
 if cid: (E/'final-inspect.json').write_text(run(['docker','inspect',cid]))
