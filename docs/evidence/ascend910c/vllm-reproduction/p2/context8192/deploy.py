import pathlib,json,subprocess,urllib.request,time,hashlib,shutil,datetime
B=pathlib.Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh'); E=B/'quality-run/context8192'; E.mkdir(exist_ok=True)
def run(a): return subprocess.check_output(a,text=True)
cid='1fdb00879533bb97ba7ef9f7bf7f64639a03e8b01bdfbdfe198b8a03fcf98a65'
r=json.loads(run(['docker','inspect',cid]))[0]
assert r['Id']==cid and r['Config']['Labels']['run_id']=='p1-vision1-20261121T205625Z-244b8fbf' and r['Config']['Labels']['owner']=='yuhao-vllm-repro'
(E/'old-inspect.json').write_text(json.dumps(r,indent=2))
for i in range(2):
 s=urllib.request.urlopen('http://127.0.0.1:18550/metrics',timeout=15).read().decode(); (E/f'old-metrics-{i}.txt').write_text(s)
 rows=[x for x in s.splitlines() if not x.startswith('#') and ('num_requests_running{' in x or 'num_requests_waiting{' in x)]
 assert len(rows)>=2 and all(float(x.split()[-1])==0 for x in rows),rows
 time.sleep(3)
p=subprocess.run(['docker','logs',cid],capture_output=True,text=True); (E/'old.log').write_text(p.stdout+p.stderr)
run(['docker','stop',cid]); (E/'fresh-npu.txt').write_text(run(['npu-smi','info'])); (E/'listeners.txt').write_text(run(['ss','-lntp']))
assert ':18550 ' not in (E/'listeners.txt').read_text()
D=B/'deployment_v3_yh'; assert not D.exists(); shutil.copytree(B/'deployment_v2_yh',D)
M=D/'docs/evidence/ascend910c/vllm-reproduction/launch/runtime-map.json'; m=json.loads(M.read_text()); old=json.loads(M.read_text()); m['environment_whitelist']['MAX_LEN']='8192'; M.write_text(json.dumps(m,indent=2)+'\n')
(E/'config-diff.json').write_text(json.dumps({'old':old['environment_whitelist'],'new':m['environment_whitelist']},indent=2))
R=D/'docs/evidence/ascend910c/vllm-reproduction/image/runtime/runtime_report-vision1.json'; rr=json.loads(R.read_text()); rr['runtime_map_sha256']=hashlib.sha256(M.read_bytes()).hexdigest(); R.write_text(json.dumps(rr,indent=2)+'\n')
a=json.loads((B/'logs/p1-vision1-20261121T205625Z-244b8fbf/argv.json').read_text()); rid='p2-8192-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'); a=[v.replace('deployment_v2_yh','deployment_v3_yh').replace('p1-vision1-20261121T205625Z-244b8fbf',rid) for v in a]; (E/'argv.json').write_text(json.dumps(a,indent=2)); (E/'run-id.txt').write_text(rid)
p=subprocess.run(a,capture_output=True,text=True); (E/'launch.log').write_text(p.stdout+p.stderr); assert p.returncode==0,p.stdout+p.stderr
(E/'container.cid').write_text((B/'runs_yh'/rid/'container.cid').read_text())
print(rid, (E/'container.cid').read_text())
