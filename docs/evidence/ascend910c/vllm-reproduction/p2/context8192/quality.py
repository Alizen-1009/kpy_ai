import pathlib,subprocess,json,time,urllib.request,traceback,os
E=pathlib.Path(__file__).resolve().parent; os.chdir(E)
B=E.parents[1]; old=E.parent/'p2-20261121T210612Z'; rid=(E/'run-id.txt').read_text(); cid=(E/'container.cid').read_text().strip()
def call(a): return subprocess.check_output(a,text=True)
def get(path): return json.load(urllib.request.urlopen('http://127.0.0.1:18550'+path,timeout=10))
def stage(a,name):
 (E/(name+'-argv.json')).write_text(json.dumps(a)); p=subprocess.run(a,capture_output=True,text=True); (E/(name+'.log')).write_text(p.stdout+p.stderr); assert p.returncode==0,(name,p.returncode)
try:
 # CLI bounds and default verified without requests; plan needs only frozen workload.
 for n,ok in [('0',False),('3601',False),('1800',True)]:
  p=subprocess.run(['python3','code128_client.py','--model',rid,'--timeout',n],capture_output=True,text=True)
  assert (p.returncode==0)==ok
 (E/'timeout-tests.json').write_text(json.dumps({'default':180,'valid':1800,'rejected':[0,3601],'compile': 'passed'}))
 deadline=time.monotonic()+2400
 while True:
  state=json.loads(call(['docker','inspect',cid]))[0]; assert state['Id']==cid and state['State']['Running']
  try: models=get('/v1/models')
  except Exception:
   assert time.monotonic()<deadline,'readiness deadline'; time.sleep(15); continue
  assert [x['id'] for x in models['data']]==[rid]; (E/'models.json').write_text(json.dumps(models)); break
 payload={'model':rid,'messages':[{'role':'user','content':'Reply only OK.'}],'max_tokens':8,'temperature':0}
 req=urllib.request.Request('http://127.0.0.1:18550/v1/chat/completions',json.dumps(payload).encode(),{'Content-Type':'application/json'})
 raw=urllib.request.urlopen(req,timeout=180).read(); (E/'smoke.response').write_bytes(raw); assert json.loads(raw)['choices'][0]['message']['content']
 (E/'READY').write_text(rid)
 stage(['python3','code128_client.py','--model',rid,'--image','sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef','--out','code128','--execute','--timeout','1800'],'code128')
 stage([str(old/'venv/bin/python'),'vision_wire.py','--server','http://127.0.0.1:18550','--model',rid,'--official-dir',str(old/'official1017'),'--out','vision23.json'],'vision23')
 (E/'QUALITY_STAGE_COMPLETE').write_text('Code8 and Vision23 finished; GSM length diagnostic still pending. No overall PASS claim.')
except Exception:
 (E/'FAILURE.txt').write_text(traceback.format_exc())
 r=json.loads(call(['docker','inspect',cid]))[0]
 if r['Id']==cid and r['Config']['Labels'].get('run_id')==rid and r['Config']['Labels'].get('owner')=='yuhao-vllm-repro': call(['docker','stop',cid])
finally:
 p=subprocess.run(['docker','logs',cid],capture_output=True,text=True); (E/'container.log').write_text(p.stdout+p.stderr)
 (E/'final-inspect.json').write_text(call(['docker','inspect',cid]))
