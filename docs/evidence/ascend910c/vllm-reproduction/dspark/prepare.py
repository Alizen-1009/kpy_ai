import pathlib,json,subprocess,hashlib,base64,datetime
R=pathlib.Path('/Users/alizen/Dev/kpy_ai'); E=pathlib.Path(__file__).parent; ref=R/'ref/deepseek-v4.1-flash-ascend910B'
m=json.loads((E.parent/'launch/restoration/dspark-runtime-map.json').read_text()); m['environment_whitelist']['MAX_LEN']='8192'
payload={}
for x in m['mounts']:
 if not x['selected']: continue
 b=subprocess.check_output(['git','-C',str(ref),'show',m['provenance']['reference_head']+':'+x['source_relative_to_ref']]); assert hashlib.sha256(b).hexdigest()==x['sha256']; payload[x['source_relative_to_ref']]=base64.b64encode(b).decode()
rid='dspark-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'); out=E/rid; out.mkdir(); (out/'runtime-map.json').write_text(json.dumps(m,indent=2)); (E/'latest.txt').write_text(rid)
code=(E/'remote.py').read_text().replace('MAP_INPUT',repr(m)).replace('PAYLOAD_INPUT',repr(payload)).replace('RUN_INPUT',repr(rid))
bench=(E.parent/'current-tps.py').read_text().replace('p2-graph-20261121T230225Z',rid).replace('range(4)','range(9)').replace("'measured_requests':3","'measured_requests':8").replace('GRAPH1 SPEC0','GRAPH1 DSPARK5')
code=code.replace("assert len(mounts)==26", "assert len(mounts)==26\n save('current-tps.py',"+repr(bench)+")")
(out/'remote.py').write_text(code)
p=subprocess.run(['ssh','-o','ConnectTimeout=20','910c','python3 -u'],input=code,text=True,capture_output=True); (out/'execution.log').write_text(p.stdout+p.stderr); print(p.stdout,p.stderr)
subprocess.run(['scp','-r','910c:/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/quality-run/'+rid+'/.',str(out)],check=True)
